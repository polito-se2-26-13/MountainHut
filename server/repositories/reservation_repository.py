from server.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple
from sqlalchemy import select,func
from server.models.DAO.user import UserDAO
from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import SlotTableDAO, TimeSlotDAO
from server.models.DAO.reservation import ReservationDAO, ReservationTableAssignmentDAO, SpecialRequirementDAO
from server.models.DTO.reservation_dto import AssignedTableInfo, ReservationCreate, SpecialRequirementDTO
from server.models.enum.reservation_status import ReservationStatus
from server.models.enum.slot_status import SlotStatus
from server.models.enum.user_type import UserType
from server.models.error.notfound_error import NotFoundError
from server.models.error.conflict_error import ConflictError
from server.service.booking_service import assign_tables_for_party
from datetime import datetime, date, time

from server.service.mapper_service import reservationTableAssignmentDAO_to_AssignedTableInfo

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
            select(ReservationDAO)
            .join(UserDAO, ReservationDAO.user_id == UserDAO.id)
            .where(
                ReservationDAO.user_id == user_id,
                ReservationDAO.slot_id == slot_id,
                ReservationDAO.status == ReservationStatus.CONFIRMED.value,
                UserDAO.role == UserType.HIKER.value
            ))
            return res.scalar_one_or_none()
    
    async def get_slot_availability(self, slot_id: int, party_size: Optional[int] = None) -> dict:
        """Free seats of a slot and, for a party size, the tables a booking would get (MH-04)."""
        slot = await self.get_time_slot(slot_id)
        if not slot:
            raise NotFoundError(f"Time slot with id {slot_id} not found.")

        # occupied_seats and free_seats of the model count only confirmed bookings, as the booking does
        tables = sorted((st for st in slot.slot_tables if st.is_available), key=lambda st: st.table.table_number)
        total_capacity = sum(st.available_seats for st in tables)
        reserved_seats = sum(st.occupied_seats for st in tables)
        remaining_seats = max(0, total_capacity - reserved_seats)
        is_open = slot.status == SlotStatus.OPEN.value

        layout = None
        if party_size is not None:
            layout = []
            if is_open:
                try:
                    # the same choice the booking makes, so the preview is what the hiker will get
                    layout = [
                        {"table_number": st.table.table_number, "assigned_seats": seats, "location": st.table.location}
                        for st, seats in assign_tables_for_party(slot, party_size)
                    ]
                except ConflictError:
                    pass
        is_available = is_open and (len(layout) > 0 if party_size is not None else remaining_seats > 0)

        layout_summary = None
        if len(layout or []) == 1:
            layout_summary = f"{party_size} seat(s) at Table {layout[0]['table_number']}"
        elif layout:
            # e.g. "2 + 3 + 1 seats", as in the MH-04 clarification
            layout_summary = f"{' + '.join(str(t['assigned_seats']) for t in layout)} seats"

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
            "is_available": is_available,
            "party_size": party_size,
            "layout_summary": layout_summary,
            "layout": layout,
            "tables": [
                {
                    "table_number": st.table.table_number,
                    "capacity": st.available_seats,
                    "occupied_seats": st.occupied_seats,
                    "free_seats": st.free_seats,
                    "location": st.table.location,
                }
                for st in tables
            ],
        }

    async def get_slot_availability_by_date_time(
        self, slot_date: date, slot_time: time, party_size: Optional[int] = None
    ) -> dict:
        """Find slot by date and time, then compute real-time availability (MH-04)."""
        async with await self._get_session() as session:
            result = await session.execute(
                select(TimeSlotDAO).where(
                    TimeSlotDAO.date == slot_date,
                    TimeSlotDAO.start_time <= slot_time,
                    TimeSlotDAO.end_time > slot_time,
                )
            )
            slot = result.scalar_one_or_none()
            if not slot:
                # If exact time range doesn't match, check by start_time
                res_start = await session.execute(
                    select(TimeSlotDAO).where(
                        TimeSlotDAO.date == slot_date,
                        TimeSlotDAO.start_time == slot_time,
                    )
                )
                slot = res_start.scalar_one_or_none()

            if not slot:
                raise NotFoundError(
                    f"Time slot not found for date '{slot_date.isoformat()}' and time '{slot_time.strftime('%H:%M')}'."
                )

        return await self.get_slot_availability(slot.id, party_size)


    async def transaction_add_reservation(self, 
        reservation:ReservationCreate,table_allocations:List[Tuple[SlotTableDAO, int]])->Tuple[ReservationDAO,List[AssignedTableInfo]]:
        async with await self._get_session() as session:
            res = ReservationDAO(
                    user_id=reservation.user_id,
                    slot_id=reservation.slot_id,
                    party_size=reservation.party_size,
                    requirements=[SpecialRequirementDAO(has_allergy=r.has_allergy, description=r.description)
                                  for r in reservation.special_requirements],
                    contact_name=reservation.contact_name,
                    contact_email=reservation.contact_email,
                    contact_phone=reservation.contact_phone,
                    status=ReservationStatus.CONFIRMED.value,
                )
            session.add(res)
            await session.flush()
            assignments:List[AssignedTableInfo]=[]
            for slot_table, seats in table_allocations:
                    table_numer=await session.execute(select(TableDAO.table_number).where(TableDAO.id==slot_table.table_id))
                    number=str(table_numer.scalar_one())
                    assignment = ReservationTableAssignmentDAO(
                        reservation_id=res.id,
                        slot_table_id=slot_table.id,
                        assigned_seats=seats,
                    )
                    session.add(assignment)
                    assignments.append(reservationTableAssignmentDAO_to_AssignedTableInfo(assignment,number))
            
            try:
                await session.commit()
                await session.refresh(res)
            except:
                await session.rollback()
                raise ValueError(f"Failed to create reservation due to database constraint")
        return [res,assignments]

    async def transaction_update_reservation(self, reservation_id: int, slot_id: int, party_size: int,
                                             requirements: Optional[List[SpecialRequirementDTO]]) -> None:
        """MH-06: a change is a new booking (PO issue #48), so the booking gives its seats back and gets its
        tables again with the MH-01 rules. If the party does not fit, nothing is saved (PO issue #38)."""
        async with await self._get_session() as session:
            reservation = await session.get(ReservationDAO, reservation_id)
            for assignment in list(reservation.table_assignments):
                await session.delete(assignment)
            await session.flush()
            # read the slot again, otherwise its free seats still count the seats given back just above
            slot = (await session.execute(
                select(TimeSlotDAO).where(TimeSlotDAO.id == slot_id).execution_options(populate_existing=True)
            )).scalar_one()
            # a ConflictError here closes the session without commit, so the booking stays as it was
            allocations = assign_tables_for_party(slot, party_size)
            reservation.slot_id = slot_id
            reservation.party_size = party_size
            if requirements is not None:
                reservation.requirements = [SpecialRequirementDAO(has_allergy=r.has_allergy, description=r.description)
                                            for r in requirements]
            for slot_table, seats in allocations:
                session.add(ReservationTableAssignmentDAO(
                    reservation_id=reservation_id, slot_table_id=slot_table.id, assigned_seats=seats))
            await session.commit()

    async def get_reservation_by_reference(self,reference:str)->tuple[ReservationDAO,list[AssignedTableInfo]]:
        async with await self._get_session() as session:
            result =await session.execute(select(
                ReservationDAO,
                ReservationTableAssignmentDAO.slot_table_id,
                ReservationTableAssignmentDAO.assigned_seats,
                TableDAO.table_number)
                    .where(ReservationTableAssignmentDAO.reservation_id==ReservationDAO.id,
                           SlotTableDAO.id==ReservationTableAssignmentDAO.slot_table_id,
                           TableDAO.id==SlotTableDAO.table_id,
                           ReservationDAO.booking_reference==reference))
        rows = result.all()
        if not rows:
            return None,[]
        
        res = rows[0][0]
        assignments:List[AssignedTableInfo]=[]
        for reservation, slot_table_id, assigned_seats , table_number in rows:
            info=AssignedTableInfo(
                table_id=slot_table_id,
                table_number=table_number,
                assigned_seats=assigned_seats
            )
            assignments.append(info)
        return res, assignments

    async def get_reservation_by_user_id(self,user_id:int)->list[tuple[ReservationDAO,list[AssignedTableInfo]]]:
            async with await self._get_session() as session:
                result =await session.execute(select(
                    ReservationDAO,
                    ReservationTableAssignmentDAO.slot_table_id,
                    ReservationTableAssignmentDAO.assigned_seats,
                    TableDAO.table_number)
                        .where(ReservationTableAssignmentDAO.reservation_id == ReservationDAO.id,
                                SlotTableDAO.id == ReservationTableAssignmentDAO.slot_table_id,
                                TableDAO.id == SlotTableDAO.table_id,
                                ReservationDAO.user_id == user_id))
            rows = result.all()
            if not rows:
                return []
            
            reservations = {}

            for res, slot_table_id, assigned_seats, table_number in rows:
                if res.id not in reservations:
                    reservations[res.id] = (res, [])

                reservations[res.id][1].append(
                    AssignedTableInfo(
                        table_id=slot_table_id,
                        table_number=table_number,
                        assigned_seats=assigned_seats
                    )
                )

            return list(reservations.values())

            
