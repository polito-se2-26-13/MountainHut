from server.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple
from sqlalchemy import select,func
from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import SlotTableDAO, TimeSlotDAO
from server.models.DAO.reservation import ReservationDAO, ReservationTableAssignmentDAO
from server.models.DTO.reservation_dto import ReservationCreate
from server.const import ReservationStatus
from server.models.error.notfound_error import NotFoundError

class ReservationRepository:

    def __init__(self, session: Optional[AsyncSession] = None):
        self._session = session

    async def _get_session(self) -> AsyncSession:
        return self._session or AsyncSessionLocal()
    
    async def get_time_slot(self,timeSlot_id:int)->TimeSlotDAO|None:
        async with await self._get_session() as session:
            result = await session.execute(
                select(TimeSlotDAO).where(TimeSlotDAO.id == timeSlot_id))
            return result.scalar_one_or_none()
    
    async def get_reservation_confirmed(self,user_id:int,slot_id:int)->ReservationDAO|None:
        async with await self._get_session() as session:
            res=await session.execute(
            select(ReservationDAO).where(
                ReservationDAO.user_id == user_id,
                ReservationDAO.slot_id == slot_id,
                ReservationDAO.status == ReservationStatus.CONFIRMED.value,
            ))
            return res.scalar_one_or_none()
    
    async def get_slot_availability(self, slot_id: int) -> dict:
        """Retrieve slot details and real-time seat availability asynchronously."""
        async with await self._get_session() as session:
            result = await session.execute(select(TimeSlotDAO).where(TimeSlotDAO.id == slot_id))
            slot = result.scalar_one_or_none()
            if not slot:
                raise NotFoundError(f"Time slot with id {slot_id} not found.")

            # Calculate capacity and reservations via direct SQL for accuracy
            cap_res = await session.execute(
                select(func.coalesce(func.sum(SlotTableDAO.available_seats), 0)).where(
                    SlotTableDAO.slot_id == slot_id,
                    SlotTableDAO.is_available == True,
                )
            )
            total_capacity = int(cap_res.scalar_one())

            res_count = await session.execute(
                select(func.coalesce(func.sum(ReservationDAO.party_size), 0)).where(
                    ReservationDAO.slot_id == slot_id,
                    ReservationDAO.status == ReservationStatus.CONFIRMED.value,
                )
            )
            reserved_seats = int(res_count.scalar_one())
            remaining_seats = max(0, total_capacity - reserved_seats)

            return {
                "slot_id": slot.id,
                "date": slot.date.isoformat(),
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
                "meal_type": slot.meal_type,
                "status": slot.status,
                "total_capacity": total_capacity,
                "reserved_seats": reserved_seats,
                "remaining_seats": remaining_seats,
            }


    async def transaction_add_reservation(self, 
        reservation:ReservationCreate,table_allocations:List[Tuple[SlotTableDAO, int]])->Tuple[ReservationDAO,List[ReservationTableAssignmentDAO]]:
        async with await self._get_session() as session:
            res = ReservationDAO(
                    user_id=reservation.user_id,
                    slot_id=reservation.slot_id,
                    party_size=reservation.party_size,
                    special_requirements=reservation.special_requirements,
                    contact_name=reservation.contact_name,
                    contact_email=reservation.contact_email,
                    contact_phone=reservation.contact_phone,
                    status=ReservationStatus.CONFIRMED.value,
                )
            session.add(res)
            await session.flush()
            assignments:List[dict]=[]
            for slot_table, seats in table_allocations:
                    table_numer=await session.execute(select(TableDAO.table_number).where(TableDAO.id==slot_table.table_id))
                    number=str(table_numer.scalar_one())
                    assignment = ReservationTableAssignmentDAO(
                        reservation_id=res.id,
                        slot_table_id=slot_table.id,
                        assigned_seats=seats,
                    )
                    session.add(assignment)
                    assignments.append({
                        "slotTableId":slot_table.id,
                        "tableNumber":number,
                        "assignedSeats":seats,
                    })
            
            try:
                await session.commit()
                await session.refresh(res)
            except:
                await session.rollback()
                raise ValueError(f"Failed to create reservation due to database constraint")
        return [res,assignments]