from typing import Optional
from server.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,func
from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import TimeSlotDAO, SlotTableDAO
from datetime import date, time, datetime

class SlotRepository:

    def __init__(self, session: Optional[AsyncSession] = None):
        self._session = session

    async def _get_session(self) -> AsyncSession:
        return self._session or AsyncSessionLocal()

    async def find_slot_time(self, date:date,startTime:time,endTime:time,mealType:str)->TimeSlotDAO|None:
        async with await self._get_session() as session:
            result = await session.execute(
                select(TimeSlotDAO).where(
                    TimeSlotDAO.date == date,
                    func.time(TimeSlotDAO.start_time) == startTime.strftime("%H:%M:%S"),
                    func.time(TimeSlotDAO.end_time) == endTime.strftime("%H:%M:%S"),
                    TimeSlotDAO.meal_type == mealType
                )
            )

            return result.scalar_one_or_none()
    
        
    async def find_table(self,table_number:str)-> TableDAO|None:
        async with await self._get_session() as session:
            result=await session.execute(select(TableDAO).where(
                TableDAO.table_number==table_number))
            return result.scalar_one_or_none()
        
    async def transaction_add_table(self,slotTime:TimeSlotDAO,tables:list[tuple[TableDAO,int]])->list:
        table_list = []
        async with await self._get_session() as session:
            try:
                for t,seat in tables:
                    slotTable=await session.execute(select(SlotTableDAO).where(
                        SlotTableDAO.table_id==t.id,
                        SlotTableDAO.slot_id==slotTime.id
                    ))
                    result=slotTable.scalar_one_or_none()
                    if result is None:
                        session.add(SlotTableDAO(
                            slot_id =slotTime.id,
                            table_id= t.id,
                            available_seats=seat,
                            is_available=True
                        ))
                    else:
                        result.available_seats = seat
                        result.is_available = True
                    table_list.append({
                        "tableNumber": t.table_number,
                        "seats": seat
                    })
                    await session.flush()

            except :
                await session.rollback()
                raise
            
            await session.commit()
            return table_list

    async def get_slot_time(self, date: Optional[date] = None):
        async with await self._get_session() as session:
            if date is None:
                query = (
                    select(TimeSlotDAO, SlotTableDAO.table_id,SlotTableDAO.available_seats
                    )
                    .where(TimeSlotDAO.id == SlotTableDAO.slot_id)
                )
            else:
                query = (
                    select(TimeSlotDAO, SlotTableDAO.table_id,SlotTableDAO.available_seats
                    )
                    .where(TimeSlotDAO.id == SlotTableDAO.slot_id, TimeSlotDAO.date==date)
                )

            result = await session.execute(query)
            rows = result.all()

            slots = {}
            for slot, table_id, available_seats in rows:
                if slot.id not in slots:
                    slots[slot.id] = [slot, []]
                if table_id is not None:
                    slots[slot.id][1].append({
                        "table_id": table_id,
                        "available_seats": available_seats
                    })
            return [
                (slot, tables)
                for slot, tables in slots.values()
            ]