from server.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple
from sqlalchemy import select
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
from datetime import date, time

from server.service.mapper_service import reservationTableAssignmentDAO_to_AssignedTableInfo,specialRequirementDTO_to_DAO

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
                raise NotFoundError(
                    f"Time slot not found for date '{slot_date.isoformat()}' and time '{slot_time.strftime('%H:%M')}'."
                )

        return await self.get_slot_availability(slot.id, party_size)


    async def transaction_add_reservation(self, 
        reservation:ReservationCreate,table_allocations:List[Tuple[SlotTableDAO, int]],requirment:list[SpecialRequirementDTO]|None)->Tuple[ReservationDAO,List[AssignedTableInfo],list[SpecialRequirementDAO]]:
        async with await self._get_session() as session:
            #add reservation
            res = ReservationDAO(
                    user_id=reservation.user_id,
                    slot_id=reservation.slot_id,
                    party_size=reservation.party_size,
                    #requirements=specialRequirementDTO_to_DAO(reservation.special_requirements),
                    contact_name=reservation.contact_name,
                    contact_email=reservation.contact_email,
                    contact_phone=reservation.contact_phone,
                    status=ReservationStatus.CONFIRMED.value,
                )
            session.add(res)
            await session.flush()
            #add table
            assignments:List[AssignedTableInfo]=[]
            for slot_table, seats in table_allocations:
                    assignment = ReservationTableAssignmentDAO(
                        reservation_id=res.id,
                        slot_table_id=slot_table.id,
                        assigned_seats=seats,
                    )
                    session.add(assignment)
                    assignments.append(reservationTableAssignmentDAO_to_AssignedTableInfo(assignment,slot_table.table.table_number))
            #add special requirment
            await session.flush()
            for s in requirment:
                spReqDAO=SpecialRequirementDAO(
                    reservation_id=res.id,
                    has_allergy=s.has_allergy,
                    description=s.description,
                )
                session.add(spReqDAO)
            await session.flush()
            try:
                await session.commit()
                await session.refresh(res)
            except:
                await session.rollback()
                raise ValueError(f"Failed to create reservation due to database constraint")
        return [res,assignments]

    async def transaction_update_reservation(self, reservation_id: int, slot_id: int, party_size: int,
                                             requirements: List[SpecialRequirementDTO]) -> None:
        """Gives the booking's seats back and assigns its tables again, all in one commit (MH-06)."""
        async with await self._get_session() as session:
            reservation = await session.get(ReservationDAO, reservation_id)
            # the booking gives its seats back: the slot stops counting them, and delete-orphan deletes them at the flush
            reservation.table_assignments.clear()
            await session.flush()
            # load the slot again with all its bookings: after the flush they would be read one by one,
            # which async SQLAlchemy cannot do (MissingGreenlet when other bookings share the slot)
            slot = await session.get(TimeSlotDAO, slot_id, populate_existing=True)
            # a ConflictError here closes the session without commit, so the booking stays as it was (PO issue #38)
            remaining = sum(st.free_seats for st in slot.slot_tables if st.is_available)
            if party_size > remaining:
                # the same check and message as a new booking
                raise ConflictError(f"Not enough seats available (requested {party_size}, remaining {remaining}).")
            allocations = assign_tables_for_party(slot, party_size)
            reservation.slot_id = slot_id
            reservation.party_size = party_size
            reservation.requirements = specialRequirementDTO_to_DAO(requirements)
            for slot_table, seats in allocations:
                session.add(ReservationTableAssignmentDAO(
                    reservation_id=reservation_id, slot_table_id=slot_table.id, assigned_seats=seats))
            await session.commit()

    async def get_reservation_by_reference(self,reference:str)->tuple[ReservationDAO,list[AssignedTableInfo],list[SpecialRequirementDTO]]:
        async with await self._get_session() as session:
            result =await session.execute(select(
                ReservationDAO,
                ReservationTableAssignmentDAO.slot_table_id,
                ReservationTableAssignmentDAO.assigned_seats,
                TableDAO.table_number,
                SpecialRequirementDAO.id,
                SpecialRequirementDAO.description,
                SpecialRequirementDAO.has_allergy
                )
                .outerjoin(
                    SpecialRequirementDAO,
                    SpecialRequirementDAO.reservation_id == ReservationDAO.id
                )
                .where(ReservationTableAssignmentDAO.reservation_id==ReservationDAO.id,
                        SlotTableDAO.id==ReservationTableAssignmentDAO.slot_table_id,
                        TableDAO.id==SlotTableDAO.table_id,
                        ReservationDAO.booking_reference==reference))
        rows = result.all()
        if not rows:
            return None,[],[]
        
        res = rows[0][0]
        assignments:List[AssignedTableInfo]=[]
        req:list[SpecialRequirementDTO]=[]
        seen_tables = set()
        seen_requirements = set()

        for _, slot_table_id, assigned_seats, table_number, req_id, sp_desc, sp_hasAllergy in rows:
            if slot_table_id not in seen_tables:
                assignments.append(
                    AssignedTableInfo(
                        table_id=slot_table_id,
                        table_number=table_number,
                        assigned_seats=assigned_seats
                    )
                )
                seen_tables.add(slot_table_id)
            if req_id is not None and req_id not in seen_requirements:
                req.append(
                    SpecialRequirementDTO(
                        description=sp_desc,
                        has_allergy=sp_hasAllergy
                    )
                )
                seen_requirements.add(req_id)
        return res, assignments, req

    async def get_reservation_by_user_id(self,user_id:int)->list[tuple[ReservationDAO,list[AssignedTableInfo],list[SpecialRequirementDTO]]]:
            async with await self._get_session() as session:
                result =await session.execute(select(
                    ReservationDAO,
                    ReservationTableAssignmentDAO.slot_table_id,
                    ReservationTableAssignmentDAO.assigned_seats,
                    TableDAO.table_number,
                    SpecialRequirementDAO.id,
                    SpecialRequirementDAO.description,
                    SpecialRequirementDAO.has_allergy)       
                .join(
                    ReservationTableAssignmentDAO,
                    ReservationTableAssignmentDAO.reservation_id == ReservationDAO.id
                )
                .join(
                    SlotTableDAO,
                    SlotTableDAO.id == ReservationTableAssignmentDAO.slot_table_id
                )
                .join(
                    TableDAO,
                    TableDAO.id == SlotTableDAO.table_id
                )
                .outerjoin(
                    SpecialRequirementDAO,
                    SpecialRequirementDAO.reservation_id == ReservationDAO.id
                )
                .where(ReservationDAO.user_id == user_id)
            )
                
            rows = result.all()
            if not rows:
                return []
            
            reservations = {}
            seen_requirements = set()
            seen_table=set()

            for res, slot_table_id, assigned_seats, table_number, req_id, req_desc, req_has_allergy in rows:
                if res.id not in reservations:
                    reservations[res.id] = (res, [], [])

                table_key=(res.id,table_number)
                if table_key not in seen_table:
                    reservations[res.id][1].append(
                        AssignedTableInfo(
                            table_id=slot_table_id,
                            table_number=table_number,
                            assigned_seats=assigned_seats
                        )
                    )
                    seen_table.add(table_key)

                if req_id is not None and req_id not in seen_requirements:
                    reservations[res.id][2].append(
                        SpecialRequirementDTO(
                            description=req_desc,
                            has_allergy=req_has_allergy
                        )
                    )
                    seen_requirements.add(req_id)
            return list(reservations.values())

            
