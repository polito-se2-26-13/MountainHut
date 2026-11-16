from server.models.enum.user_type import UserType
from server.repositories.reservation_repository import ReservationRepository
from server.models.DTO.reservation_dto import ReservationCreate,ReservationResponse
from server.models.DAO.time_slot import TimeSlotDAO
from server.models.error.notfound_error import NotFoundError
from server.models.error.conflict_error import ConflictError
from server.models.error.forbidden_error import ForbiddenError
from server.models.enum.slot_status import SlotStatus
from server.service.booking_service import validate_two_hour_rule,assign_tables_for_party,validate_change_deadline
from server.service.mapper_service import reservationDTO_to_response,reservationEmailDto_to_email
from server.service.email_service import send_booking_confirmation_email, send_booking_change_email
from fastapi import BackgroundTasks
import asyncio
import time

# One booking at a time between the check of the free seats and the save, otherwise two bookings sent
# at the same moment both see the same free seats. Whoever takes or gives back seats (also the change of
# a booking, MH-06) uses this same lock.
# shortcut: it works inside one server process, which is how it runs also in Docker; with more processes
# the lock has to move to the database (a transaction started with BEGIN IMMEDIATE in SQLite)
booking_lock = asyncio.Lock()


def send_confirmation_with_retry(mail, waits=(5, 10)):
    """Sends the confirmation, trying again after 5 and then 10 seconds.
    It runs after the answer, so the booking stands anyway and a failure is only written in the log."""
    for wait in (*waits, None):
        result = send_booking_confirmation_email(mail)
        if result["status"] == "SENT" or wait is None:
            break
        time.sleep(wait)
    if result["status"] != "SENT":
        # flush, otherwise the line waits in a buffer when the output goes to a file or to Docker
        print(f"confirmation email not sent for {mail.booking_reference}: {result.get('error')}", flush=True)


class ReservationController():
    def __init__(self):
        self.repo=ReservationRepository()

    async def create_reservation(self,reservation:ReservationCreate,background_tasks:BackgroundTasks|None=None)->ReservationResponse:
        """Creation reservation"""
        # the slot is read inside the lock, so its free seats already count the booking saved just before
        async with booking_lock:
            #check time slot
            timeSlot=await self.repo.get_time_slot(reservation.slot_id)
            if timeSlot is None:
                raise NotFoundError("time slot not foud")

            #check aviabililty
            if timeSlot.status!=SlotStatus.OPEN:
                raise ConflictError("time slot is not open")

            #check two hour rule
            validate_two_hour_rule(timeSlot,None)

            # Check rule: Only one booking per time slot on a date per hiker
            existing_booking_res = await self.repo.get_reservation_confirmed(reservation.user_id,reservation.slot_id)
            if existing_booking_res is not None:
                raise ConflictError("Hiker already has a confirmed booking for this time slot.")

            # Check available capacity (Capacity Deduction constraint)
            avail = await self.repo.get_slot_availability(reservation.slot_id)
            if reservation.party_size > avail["remaining_seats"]:
                raise ConflictError(
                    f"Not enough seats available (requested {reservation.party_size}, remaining {avail['remaining_seats']})."
                )
            #allocation
            table_allocations = assign_tables_for_party(timeSlot, reservation.party_size)
            res,tables= await self.repo.transaction_add_reservation(reservation,table_allocations)
        mail=reservationEmailDto_to_email(
                res.booking_reference,
                res.contact_email,
                timeSlot.date.strftime("%d/%m/%Y"),
                f"{timeSlot.start_time:%H:%M}-{timeSlot.end_time:%H:%M}",
                res.party_size,
                res.special_requirements_list or res.special_requirements,
                res.hiker.full_name
            )
        # the answer does not wait for the mail server, which kept the whole backend busy for up to 20 seconds
        if background_tasks is not None:
            background_tasks.add_task(send_confirmation_with_retry,mail)
        else:
            send_confirmation_with_retry(mail)
        return reservationDTO_to_response(res,tables)

    async def get_reservation_by_reference(self,reference:str,user_id:int,role:UserType):
        res,tables= await self.repo.get_reservation_by_reference(reference)
        if not res :
            raise NotFoundError("booking reference not found")
        if res.user_id!=user_id and role==UserType.HIKER:
            raise ForbiddenError("you cannot see other reservation")
        return reservationDTO_to_response(res,tables)

    async def get_reservation_by_user_id(self,user_id:int):
            res= await self.repo.get_reservation_by_user_id(user_id)
            listRes=[]
            for r,a in res:
                listRes.append(reservationDTO_to_response(r,a))
            return listRes

    async def update_reservation(
        self,
        reference: str,
        user_id: int,
        changes,
        background_tasks: BackgroundTasks | None = None,
    ) -> ReservationResponse:
        async with booking_lock:
            current, _ = await self.repo.get_reservation_by_reference(reference)
            if current is None or current.user_id != user_id:
                raise ForbiddenError("you cannot change this reservation")
            if current.status != "CONFIRMED":
                raise ConflictError("only confirmed bookings can be changed")

            validate_change_deadline(current.slot)

            target_slot_id = changes.slot_id if changes.slot_id is not None else current.slot_id
            if target_slot_id != current.slot_id:
                # in another slot it is a new booking there, so the MH-01 rules hold (PO issues #38 and #48)
                new_slot = await self.repo.get_time_slot(target_slot_id)
                if new_slot is None:
                    raise NotFoundError("time slot not found")
                validate_two_hour_rule(new_slot, None)
            target_party_size = changes.party_size if changes.party_size is not None else current.party_size
            requirements_changed = "special_requirements" in changes.model_fields_set
            target_requirements = changes.special_requirements if requirements_changed else None
            _, _, previous_slot, previous_party_size = (
                await self.repo.transaction_update_reservation(
                    reference,
                    user_id,
                    target_slot_id,
                    target_party_size,
                    target_requirements,
                )
            )

        # read again and build the mail as the confirmation does: the mail no longer touches a closed session,
        # it has no table numbers (PO issue #24) and it marks the allergies
        res, tables = await self.repo.get_reservation_by_reference(reference)
        mail = reservationEmailDto_to_email(
            res.booking_reference,
            res.contact_email,
            res.slot.date.strftime("%d/%m/%Y"),
            f"{res.slot.start_time:%H:%M}-{res.slot.end_time:%H:%M}",
            res.party_size,
            res.special_requirements_list or res.special_requirements,
            res.hiker.full_name,
        )
        if background_tasks is not None:
            background_tasks.add_task(send_booking_change_email, mail, previous_slot, previous_party_size)
        else:
            send_booking_change_email(mail, previous_slot, previous_party_size)
        return reservationDTO_to_response(res, tables)