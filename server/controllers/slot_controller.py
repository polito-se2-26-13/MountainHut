from server.models.DAO.table import TableDAO
from server.models.DTO.slot_dto import SlotCreation
from server.repositories.slot_repopsitory import SlotRepository
from server.repositories.reservation_repository import ReservationRepository
from server.models.error.conflict_error import ConflictError
from server.models.error.notfound_error import NotFoundError
from server.service.mapper_service import slotTableDto_to_response
from server.models.error.unprocessable_content import UnprocessableContent
from server.models.DTO.slot_dto import SlotDetail
from server.service.mapper_service import slots_deatils_to_response
from datetime import date, datetime

class SlotController():
    def __init__(self):
        self.repo=SlotRepository()

    async def setUpSlot(self,slot: SlotCreation):
        if(slot.startTime>=slot.endTime):
            raise UnprocessableContent("start time must be less then end time")
        if datetime.combine(slot.date,slot.startTime)<datetime.now():
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
        # PO issue 31: two slots of the same day can follow each other but cannot overlap
        if await self.repo.find_overlapping_slot(slot.date,slot.startTime,slot.endTime):
            raise ConflictError("the slot overlaps another slot of the same day")

        #search time slot, or create it: the employee chooses date and times freely (MH-02)
        slotTime=await self.repo.find_slot_time(slot.date,slot.startTime,slot.endTime,slot.mealType)
        if slotTime is None:
            raise NotFoundError("Time Slot doesn't exist")
            #slotTime=await self.repo.add_slot_time(slot)
        else:
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
                raise NotFoundError(f"table {t.tableNumber} not foud")
                #table=await self.repo.add_table(t.tableNumber,t.seats)
            if table.capacity<t.seats:
                # conflict error when trying to arrange more tables than the table's capacity allows
                raise ConflictError(f"You cannot add {t.seats} seats to table {t.tableNumber} because it exceeds the capacity: {table.capacity}.")
            tables.append((table,t.seats))
        #add table
        result=await self.repo.transaction_add_table(slotTime,tables)
        return slotTableDto_to_response(slotTime,result)

    async def getSlotTime(self,date:date)->list[SlotDetail]:
        result=await self.repo.get_slot_time(date)
        return slots_deatils_to_response(result)

    async def getSlotAvailability(self,slot_id:int)->dict:
        return await ReservationRepository().get_slot_availability(slot_id)