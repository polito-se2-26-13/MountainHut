from server.repositories.reservation_repository import ReservationRepository
from server.models.DTO.reservation_dto import ReservationCreate,ReservationResponse
from server.models.DAO.time_slot import TimeSlotDAO
from server.models.error.notfound_error import NotFoundError
from server.models.error.conflict_error import ConflictError
from server.const import SlotStatus
from server.service.booking_service import validate_two_hour_rule,assign_tables_for_party
from server.service.mapper_service import reservationDTO_to_response,reservationEmailDto_to_email
from server.service.email_service import send_booking_confirmation_email
class ReservationController():
    def __init__(self):
        self.repo=ReservationRepository()

    async def create_reservation(self,reservation:ReservationCreate)->ReservationResponse:
        """Creation reservation"""
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
        mail=send_booking_confirmation_email(
            reservationEmailDto_to_email(
                res.booking_reference,
                res.contact_email,
                timeSlot.date.strftime("%d/%m/%Y"),
                f"{timeSlot.start_time:%H:%M}-{timeSlot.end_time:%H:%M}",
                res.party_size,
                res.special_requirements,
                res.hiker.full_name
            )
        )
        # the booking stands even if the mail fails, and this is the only trace of it
        if mail["status"]!="SENT":
            print(f"confirmation email not sent for {res.booking_reference}: {mail['error']}")
        return reservationDTO_to_response(res,tables)

    async def get_reservation_by_reference(self,reference:str):
        res,tables= await self.repo.get_reservation_by_reference(reference)
        if not res :
            raise NotFoundError("booking reference not found")
        
        return reservationDTO_to_response(res,tables)

    async def get_reservation_by_user_id(self,user_id:str):
            res= await self.repo.get_reservation_by_user_id(user_id)
            if not res :
                raise NotFoundError(f"booking for id {user_id} not found")
            listRes=[]
            for r,a in res:
                listRes.append(reservationDTO_to_response(r,a))
            return listRes