from server.models.DAO.table import TableDAO
from server.models.DTO.slot_dto import SlotCreation
from server.repositories.slot_repopsitory import SlotRepository
from server.repositories.reservation_repository import ReservationRepository
from server.controllers.reservation_controller import booking_lock
from server.models.error.conflict_error import ConflictError
from server.service.mapper_service import slotTableDto_to_response, timeSlotDAO_to_response,tableDAO_to_response
from server.models.error.unprocessable_content import UnprocessableContent
from server.models.DTO.slot_dto import SlotDetail
from server.models.DTO.time_dto import TimeResponse
from server.models.DTO.table_dto import TableResponse
from server.service.mapper_service import slots_deatils_to_response
from datetime import date, datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

class SlotController():
    def __init__(self):
        self.repo=SlotRepository()

    async def setUpSlot(self,slot: SlotCreation):
        # an offset like 12:00+01:00 cannot be compared with a time without it, which gave a 500
        if slot.startTime.tzinfo or slot.endTime.tzinfo:
            raise UnprocessableContent("times are Italian times, without a UTC offset")
        if(slot.startTime>=slot.endTime):
            raise UnprocessableContent("start time must be less then end time")
        # slot times are Italian, the server clock may not be (Docker runs in UTC)
        italy_tz=ZoneInfo("Europe/Rome")
        if datetime.combine(slot.date,slot.startTime,tzinfo=italy_tz)<datetime.now(italy_tz):
            raise UnprocessableContent("the slot is in the past")
        # checked before saving anything, so a refused request leaves no slot or table behind
        names=set()
        for t in slot.tables:
            if t.seats<=0:
                raise UnprocessableContent("seats can not be negative or 0")
            t.tableNumber=t.tableNumber.strip()
            if not t.tableNumber or len(t.tableNumber)>50:
                raise UnprocessableContent("a table needs a name of 1 to 50 characters")
            # the same name twice would save one table only, with the seats of the second
            if t.tableNumber in names:
                raise UnprocessableContent(f"table {t.tableNumber} is written twice")
            names.add(t.tableNumber)
        # the lock of the bookings: no booking lands between the check of the booked seats and the save,
        # and two equal saves sent together cannot both create the slot
        async with booking_lock:
            # PO issue 31: two slots of the same day can follow each other but cannot overlap
            if await self.repo.find_overlapping_slot(slot.date,slot.startTime,slot.endTime):
                raise ConflictError("the slot overlaps another slot of the same day")

            #search time slot, or create it: the employee chooses date and times freely (MH-02)
            slotTime=await self.repo.find_slot_time(slot.date,slot.startTime,slot.endTime)
            if slotTime is None:
                slotTime=await self.repo.add_slot_time(slot)
            else:
                # saving the same times again updates that slot, also its meal when one is chosen
                if slot.mealType:
                    slotTime.meal_type=slot.mealType
                # saving the slot again cannot leave a table with fewer seats than the ones already booked on it
                booked={st.table.table_number: st.occupied_seats for st in slotTime.slot_tables}
                for t in slot.tables:
                    if t.seats<booked.get(t.tableNumber,0):
                        raise ConflictError(f"table {t.tableNumber} already has {booked[t.tableNumber]} seats booked")

            #search table, or create it: there is no fixed set of tables and seats differ per slot (PO issue 17)
            tables: list[tuple[TableDAO,int]]=[]
            for t in slot.tables:
                table=await self.repo.find_table(t.tableNumber)
                if table is None:
                    table=await self.repo.add_table(t.tableNumber,t.seats)
                tables.append((table,t.seats))
            #add table
            result=await self.repo.transaction_add_table(slotTime,tables)
        return slotTableDto_to_response(slotTime,result)

    async def getSlotTime(self,date:date)->list[SlotDetail]:
        result=await self.repo.get_slot_time(date)
        return slots_deatils_to_response(result)

    async def getSlotAvailability(self, slot_id: int, party_size: Optional[int] = None) -> dict:
        return await ReservationRepository().get_slot_availability(slot_id, party_size)

    async def getSlotAvailabilityByDateTime(
        self, slot_date: date, slot_time: Optional[time], party_size: Optional[int] = None
    ) -> list[dict]:
        return await ReservationRepository().get_slot_availability_by_date_time(slot_date, slot_time, party_size)

    async def get_list_time(self)->list[TimeResponse]:
        result=await self.repo.get_time()
        response:list[TimeResponse]=[]
        for r in result:
            response.append(timeSlotDAO_to_response(r))
        return response

    async def get_list_table(self)->list[TableResponse]:
            result=await self.repo.get_table()
            response:list[TableResponse]=[]
            for r in result:
                response.append(tableDAO_to_response(r))
            return response
