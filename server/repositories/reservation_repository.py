from server.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import SlotTableDAO, TimeSlotDAO
from server.models.DAO.reservation import (
    ReservationDAO,
    ReservationTableAssignmentDAO,
    SpecialRequirementDAO,
)
from server.models.DTO.reservation_dto import ReservationCreate, SpecialRequirementDTO
from server.const import ReservationStatus, SlotStatus
from server.models.error.notfound_error import NotFoundError
from datetime import datetime, date, time

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
    
    async def get_slot_availability(self, slot_id: int, party_size: Optional[int] = None) -> dict:
        """Retrieve slot details, real-time seat availability, and party table layout (MH-04)."""
        async with await self._get_session() as session:
            result = await session.execute(select(TimeSlotDAO).where(TimeSlotDAO.id == slot_id))
            slot = result.scalar_one_or_none()
            if not slot:
                raise NotFoundError(f"Time slot with id {slot_id} not found.")

            # Grouped query to calculate per-table capacity, occupancy, and free seats
            table_query = await session.execute(
                select(
                    SlotTableDAO.id.label("slot_table_id"),
                    TableDAO.id.label("table_id"),
                    TableDAO.table_number,
                    TableDAO.capacity.label("table_capacity"),
                    TableDAO.location,
                    SlotTableDAO.available_seats,
                    func.coalesce(func.sum(ReservationTableAssignmentDAO.assigned_seats), 0).label("occupied_seats"),
                )
                .join(TableDAO, TableDAO.id == SlotTableDAO.table_id)
                .outerjoin(
                    ReservationTableAssignmentDAO,
                    ReservationTableAssignmentDAO.slot_table_id == SlotTableDAO.id,
                )
                .outerjoin(
                    ReservationDAO,
                    (ReservationDAO.id == ReservationTableAssignmentDAO.reservation_id)
                    & (ReservationDAO.status == ReservationStatus.CONFIRMED.value),
                )
                .where(
                    SlotTableDAO.slot_id == slot_id,
                    SlotTableDAO.is_available == True,
                )
                .group_by(
                    SlotTableDAO.id,
                    TableDAO.id,
                    TableDAO.table_number,
                    TableDAO.capacity,
                    TableDAO.location,
                    SlotTableDAO.available_seats,
                )
                .order_by(TableDAO.table_number.asc())
            )
            rows = table_query.all()

            tables_info = []
            free_tables = []
            total_capacity = 0
            reserved_seats = 0

            for r in rows:
                avail = int(r.available_seats)
                occ = int(r.occupied_seats)
                free = max(0, avail - occ)
                total_capacity += avail
                reserved_seats += occ
                tables_info.append({
                    "table_number": r.table_number,
                    "capacity": avail,
                    "occupied_seats": occ,
                    "free_seats": free,
                    "location": r.location,
                })
                if free > 0:
                    free_tables.append({
                        "table_number": r.table_number,
                        "free_seats": free,
                        "location": r.location,
                    })

            remaining_seats = max(0, total_capacity - reserved_seats)
            is_open = (slot.status == SlotStatus.OPEN.value)
            is_available = is_open and (remaining_seats > 0 if party_size is None else remaining_seats >= party_size)

            layout = None
            layout_summary = None

            if party_size is not None:
                if not is_open or party_size > remaining_seats:
                    is_available = False
                    layout = []
                    layout_summary = None
                else:
                    # 1. Single table priority (keep party together on single table)
                    single_fits = [t for t in free_tables if t["free_seats"] >= party_size]
                    if single_fits:
                        chosen = min(single_fits, key=lambda t: t["free_seats"])
                        layout = [{
                            "table_number": chosen["table_number"],
                            "assigned_seats": party_size,
                            "location": chosen["location"],
                        }]
                        layout_summary = f"{party_size} seat(s) at Table {chosen['table_number']}"
                    else:
                        # 2. Minimal multi-table split (MH-01 & MH-04)
                        sorted_tables = sorted(free_tables, key=lambda t: t["free_seats"], reverse=True)
                        needed = next(
                            (n for n in range(2, len(sorted_tables) + 1)
                             if sum(t["free_seats"] for t in sorted_tables[:n]) >= party_size),
                            None,
                        )
                        if needed is None:
                            is_available = False
                            layout = []
                            layout_summary = None
                        else:
                            # Dynamic programming best-fit to find minimal excess free seats
                            sets = [{} for _ in range(needed + 1)]
                            sets[0][0] = []
                            for t in sorted_tables:
                                s = t["free_seats"]
                                for k in range(needed - 1, -1, -1):
                                    for total, tbls in list(sets[k].items()):
                                        if total + s not in sets[k + 1]:
                                            sets[k + 1][total + s] = tbls + [t]

                            valid_totals = [tot for tot in sets[needed] if tot >= party_size]
                            if not valid_totals:
                                is_available = False
                                layout = []
                                layout_summary = None
                            else:
                                best_total = min(valid_totals)
                                chosen_tables = sets[needed][best_total]

                                layout = []
                                rem = party_size
                                seat_counts = []
                                for t in sorted(chosen_tables, key=lambda x: x["free_seats"], reverse=True):
                                    take = min(t["free_seats"], rem)
                                    layout.append({
                                        "table_number": t["table_number"],
                                        "assigned_seats": take,
                                        "location": t["location"],
                                    })
                                    seat_counts.append(take)
                                    rem -= take
                                # Format matching Story 4 specification: e.g. "2 + 3 + 1 seats"
                                layout_summary = f"{' + '.join(str(s) for s in seat_counts)} seats"

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
                "tables": tables_info,
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
        reservation:ReservationCreate,table_allocations:List[Tuple[SlotTableDAO, int]])->Tuple[ReservationDAO,List[ReservationTableAssignmentDAO]]:
        async with await self._get_session() as session:
            # Normalise special_requirements to a plain string for the legacy TEXT column
            sp_req_str: Optional[str] = None
            if reservation.special_requirements:
                items = reservation.special_requirements
                if isinstance(items, str):
                    sp_req_str = items
                else:
                    sp_req_str = "; ".join(
                        f"{'[ALLERGY] ' if r.has_allergy else ''}{r.description}"
                        for r in items
                        if r.description.strip()
                    ) or None

            res = ReservationDAO(
                    user_id=reservation.user_id,
                    slot_id=reservation.slot_id,
                    party_size=reservation.party_size,
                    special_requirements=sp_req_str,
                    contact_name=reservation.contact_name,
                    contact_email=reservation.contact_email,
                    contact_phone=reservation.contact_phone,
                    status=ReservationStatus.CONFIRMED.value,
                )
            session.add(res)
            await session.flush()

            # Atomically persist structured special requirements (MH-05)
            if reservation.special_requirements:
                items = reservation.special_requirements
                if isinstance(items, str):
                    items = [SpecialRequirementDTO(has_allergy=False, description=items)]
                for req in items:
                    if req.description.strip():
                        sr = SpecialRequirementDAO(
                            reservation_id=res.id,
                            has_allergy=req.has_allergy,
                            description=req.description.strip(),
                        )
                        session.add(sr)
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
                        "tableLocation":""
                    })
            
            try:
                await session.commit()
                await session.refresh(res)
            except:
                await session.rollback()
                raise ValueError(f"Failed to create reservation due to database constraint")
        return [res,assignments]

    async def get_reservation_by_reference(self,reference:str)->tuple[ReservationDAO,list[dict]]:
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
        assignments:List[dict]=[]
        for reservation, slot_table_id, assigned_seats , table_number in rows:
            assignments.append({
                "slotTableId": slot_table_id,
                "tableNumber": table_number,
                "assignedSeats": assigned_seats
            })
        return res, assignments

    async def get_reservation_by_user_id(self,user_id:str)->tuple[ReservationDAO,list[dict]]:
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
                    reservations[res.id] = [res, []]

                reservations[res.id][1].append(({
                    "slotTableId": slot_table_id,
                    "assignedSeats": assigned_seats,
                    "tableNumber": table_number
                }))
            return [
                (res, assignments)
                for res, assignments in reservations.values()
            ]

            
