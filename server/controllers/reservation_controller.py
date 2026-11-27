from typing import Optional

from server.models.DAO.user import UserDAO
from server.models.enum.user_type import UserType
from server.repositories.reservation_repository import ReservationRepository
from server.models.DTO.reservation_dto import ReservationCreate, ReservationHinkerCreate, ReservationMailDTO,ReservationResponse,ReservationUpdate
from server.models.DAO.time_slot import TimeSlotDAO
from server.models.error.notfound_error import NotFoundError
from server.models.error.conflict_error import ConflictError
from server.models.error.forbidden_error import ForbiddenError
from server.models.enum.slot_status import SlotStatus
from server.models.enum.reservation_status import ReservationStatus
from server.service.booking_service import validate_two_hour_rule,assign_tables_for_party,validate_change_deadline
from server.service.mapper_service import UserDetailRes_to_UserCreateDTO, reservationDTO_to_response,reservationEmailDto_to_email, reservationHinkerCreate_to_reservationCreate
from server.service.email_service import send_booking_confirmation_email,send_password_to_user_email
from server.controllers.user_controller import UserController
from server.models.enum.hinker_type import HinkerType
from fastapi import BackgroundTasks
from server.models.DTO.user_dto import UserCreateDTO, UserDetailReservationDTO, UserResponseDTO
from server.repositories.user_repository import UserRepository
import asyncio
import time
import secrets
import string

# One booking at a time between the check of the free seats and the save, otherwise two bookings sent
# at the same moment both see the same free seats. Whoever takes or gives back seats (also the change of
# a booking, MH-06) uses this same lock.
# shortcut: it works inside one server process, which is how it runs also in Docker; with more processes
# the lock has to move to the database (a transaction started with BEGIN IMMEDIATE in SQLite)
booking_lock = asyncio.Lock()

def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def send_confirmation_with_retry(mail_type,content,to:str, waits=(5, 10)):
    """Sends the confirmation, trying again after 5 and then 10 seconds.
    It runs after the answer, so the booking stands anyway and a failure is only written in the log."""
    for wait in (*waits, None):
        result = mail_type(content)
        if result["status"] == "SENT" or wait is None:
            break
        time.sleep(wait)
    if result["status"] != "SENT":
        # flush, otherwise the line waits in a buffer when the output goes to a file or to Docker
        print(f"confirmation email not sent for {to}: {result.get('error')}", flush=True)


def confirm_by_mail(res,background_tasks:BackgroundTasks|None,changed:bool=False):
    """Mail of a new or a changed booking, with its details as they are now (MH-03, PO issue #41)"""
    mail:ReservationMailDTO=reservationEmailDto_to_email(
            res.booking_reference,
            res.contact_email,
            res.slot.date.strftime("%d/%m/%Y"),
            f"{res.slot.start_time:%H:%M}-{res.slot.end_time:%H:%M}",
            res.party_size,
            res.requirements,
            res.hiker.full_name,
            changed
        )
    # the answer does not wait for the mail server, which kept the whole backend busy for up to 20 seconds
    if background_tasks is not None:
        background_tasks.add_task(send_confirmation_with_retry,send_booking_confirmation_email,mail,mail.contact_email)
    else:
        send_confirmation_with_retry(send_booking_confirmation_email,mail)

def information_email_new_user(user:UserCreateDTO,background_tasks:BackgroundTasks|None):
    """Mail to inform the new user for the password"""
    #we can be change if need to send other mail type: Ask to Andrea
    if background_tasks is not None:
            background_tasks.add_task(send_confirmation_with_retry,send_password_to_user_email,user,user.email)
    else:
        send_confirmation_with_retry(send_password_to_user_email,user,user.email)

class ReservationController():
    def __init__(self):
        self.repo=ReservationRepository()

    async def _check_user(type:HinkerType,user_info:UserDetailReservationDTO,background_task:BackgroundTasks|None)->int|None:
        """Create account if needed"""
        
        if type==HinkerType.NEW:
            psw=generate_password()
            user=UserDetailRes_to_UserCreateDTO(user_info,psw)
            user.must_change_password=True
            new_user:UserResponseDTO=await UserController.create_user(user)
            user_id=new_user.id
            information_email_new_user(user,background_task)
        elif type== HinkerType.PRESENT:
            user:UserDAO=await UserRepository.get_user(user_info.id)
            if user is None:
                raise NotFoundError("accout not found")
            if  user.role != UserType.HIKER or user.is_active==False:
                raise ConflictError(f"cannot create a reservation for an user that have role {user.role}")
            user_id=user_id
        elif type== HinkerType.TEMPORARY:
            user_id=None
        else:
            raise ConflictError(f"\"{type}\" doesn't exit as type of hiker")
        return user_id

    async def _check_slot_for_booking(self,two_hours_check:bool,slot_id:int,user_id:Optional[int]=None)->TimeSlotDAO:
        """MH-01 rules of the slot, for a new booking and for a booking moved there (MH-06)"""
        """for employee booking, avoid controll on 2h"""
        #check time slot
        timeSlot=await self.repo.get_time_slot(slot_id)
        if timeSlot is None:
            raise NotFoundError("time slot not found")

        #check aviabililty
        if timeSlot.status!=SlotStatus.OPEN:
            raise ConflictError("time slot is not open")

        #check two hour rule
        if two_hours_check:
            validate_two_hour_rule(timeSlot,None)

        # Check rule: Only one booking per time slot on a date per hiker
        if slot_id is not None and await self.repo.get_reservation_confirmed(user_id,slot_id) is not None:
            raise ConflictError("Hiker already has a confirmed booking for this time slot.")
        return timeSlot

    async def _own_reservation(self,reference:str,user_id:int,role:UserType):
        """The booking with its tables: a hiker reaches only their own bookings, the hut staff all of them"""
        res,tables= await self.repo.get_reservation_by_reference(reference)
        if not res :
            raise NotFoundError("booking reference not found")
        if res.user_id!=user_id and role==UserType.HIKER:
            raise ForbiddenError("you cannot see other reservation")
        return res,tables

    async def create_reservation(self,reservation:ReservationCreate,background_tasks:BackgroundTasks|None=None)->ReservationResponse:       
        """Creation reservation for hinker"""
        # the slot is read inside the lock, so its free seats already count the booking saved just before
        async with booking_lock:

            timeSlot=await self._check_slot_for_booking(True,reservation.slot_id,reservation.user_id)

            # Check available capacity (Capacity Deduction constraint), on the slot just read, as the change does
            remaining = sum(st.free_seats for st in timeSlot.slot_tables if st.is_available)
            if reservation.party_size > remaining:
                raise ConflictError(
                    f"Not enough seats available (requested {reservation.party_size}, remaining {remaining})."
                )
            #allocation
            table_allocations = assign_tables_for_party(timeSlot, reservation.party_size)
            res,tables= await self.repo.transaction_add_reservation(reservation,table_allocations)
        confirm_by_mail(res,background_tasks)
        return reservationDTO_to_response(res,tables)

    async def get_reservation_by_reference(self,reference:str,user_id:int,role:UserType):
        res,tables= await self._own_reservation(reference,user_id,role)
        return reservationDTO_to_response(res,tables)

    async def get_reservation_by_user_id(self,user_id:int):
            res= await self.repo.get_reservation_by_user_id(user_id)
            listRes=[]
            for r,a in res:
                listRes.append(reservationDTO_to_response(r,a))
            return listRes

    async def update_reservation(self,reference:str,user_id:int,changes:ReservationUpdate,background_tasks:BackgroundTasks|None=None)->ReservationResponse:
        """Change of a booking (MH-06): it is treated as a new booking, so the MH-01 rules hold (PO issues #38 and #48)"""
        async with booking_lock:
            current,_= await self._own_reservation(reference,user_id,UserType.HIKER)
            if current.status!=ReservationStatus.CONFIRMED.value:
                raise ConflictError("only confirmed bookings can be changed")
            # PO issue #43: until 48 hours before the old slot, and before the new one too
            validate_change_deadline(current.slot)
            if changes.slot_id!=current.slot_id:
                validate_change_deadline(await self._check_slot_for_booking(changes.slot_id,user_id))
            elif current.slot.status!=SlotStatus.OPEN:
                raise ConflictError("time slot is not open")
            await self.repo.transaction_update_reservation(current.id,changes.slot_id,changes.party_size,changes.special_requirements)

        # read again, so the answer and the email show the booking as it is now
        res,tables= await self.repo.get_reservation_by_reference(reference)
        confirm_by_mail(res,background_tasks,changed=True)
        return reservationDTO_to_response(res,tables)

    async def create_reservation_for_hinker(self,reservation:ReservationHinkerCreate,background_tasks:BackgroundTasks|None=None):
        """Creation reservation"""
        async with booking_lock:
            user_id=await self._check_user(reservation.hiker_typer,reservation.user_info,background_tasks)        
            timeSlot=await self._check_slot_for_booking(False,reservation.slot_id,user_id)

            # Check available capacity (Capacity Deduction constraint), on the slot just read, as the change does
            remaining = sum(st.free_seats for st in timeSlot.slot_tables if st.is_available)
            if reservation.party_size > remaining:
                raise ConflictError(
                    f"Not enough seats available (requested {reservation.party_size}, remaining {remaining})."
                )
            #allocation
            table_allocations = assign_tables_for_party(timeSlot, reservation.party_size)
            new_res=reservationHinkerCreate_to_reservationCreate(reservation,user_id)
            res,tables= await self.repo.transaction_add_reservation(new_res,table_allocations)
        confirm_by_mail(res,background_tasks)
        return reservationDTO_to_response(res,tables)