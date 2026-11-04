from server.models.DAO.table import TableDAO
from server.models.DTO.slot_dto import SlotCreation
from server.repositories.slot_repopsitory import SlotRepository
from server.repositories.reservation_repository import ReservationRepository
from server.models.error.conflict_error import ConflictError
from server.service.mapper_service import slotTableDto_to_response
from server.models.error.unprocessable_content import UnprocessableContent
from server.models.DTO.slot_dto import SlotDetail
from server.service.mapper_service import slots_deatils_to_response
from datetime import date

class SlotController():
    def __init__(self):
        self.repo=SlotRepository()

    async def setUpSlot(self,slot: SlotCreation):
        if(slot.startTime>=slot.endTime):
            raise ConflictError("start time must be less then end time")
        # checked before saving anything, so a refused request leaves no slot or table behind
        for t in slot.tables:
            if t.seats<=0:
                raise UnprocessableContent("seats can not be negative or 0")

        #search time slot, or create it: the employee chooses date and times freely (MH-02)
        slotTime=await self.repo.find_slot_time(slot.date,slot.startTime,slot.endTime)
        if slotTime is None:
            slotTime=await self.repo.add_slot_time(slot)

        #search table, or create it: there is no fixed set of tables and seats differ per slot (#17)
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

    async def getSlotAvailability(self,slot_id:int)->dict:
        return await ReservationRepository().get_slot_availability(slot_id)