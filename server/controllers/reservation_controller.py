from server.repositories.reservation_repository import ReservationRepository
from server.models.DTO.reservation_dto import ReservationCreate,ReservationResponse
from server.models.DAO.time_slot import TimeSlotDAO
from server.models.error.notfound_error import NotFoundError
from server.models.error.conflict_error import ConflictError
from server.const import SlotStatus
from server.service.booking_service import validate_two_hour_rule,assign_tables_for_party
from server.service.mapper_service import reservationDTO_to_response
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
        return reservationDTO_to_response(res,tables)
