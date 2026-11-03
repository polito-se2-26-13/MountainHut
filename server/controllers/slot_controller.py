from server.models.DAO.table import TableDAO
from server.models.DTO.slot_dto import SlotCreation
from server.repositories.slot_repopsitory import SlotRepository
from server.models.error.conflict_error import ConflictError
from server.models.error.notfound_error import NotFoundError
from server.service.mapper_service import slotTableDto_to_response
from server.models.error.unprocessable_content import UnprocessableContent
class SlotController():
    def __init__(self):
        self.repo=SlotRepository()

    async def setUpSlot(self,slot: SlotCreation):
        #search time slot
        if(slot.startTime>=slot.endTime):
            raise ConflictError("start time must be less then end time")
        slotTime=await self.repo.find_slot_time(slot.date,slot.startTime,slot.endTime,slot.mealType)
        if slotTime is None:
            raise NotFoundError("slot time not found")

        #search table
        tables: list[tuple[TableDAO,int]]=[]
        for t in slot.tables:
            table=await self.repo.find_table(t.tableNumber)
            if table is None:
                raise NotFoundError(f"table {t.tableNumber} not found")
            if t.seats>table.capacity:
                raise ConflictError(f"you can not add more seats tath the capacity of the table")
            tables.append((table,t.seats))
            if t.seats<=0:
                raise UnprocessableContent("seats can not be negative or 0")
        #add table
        result=await self.repo.transaction_add_table(slotTime,tables)
        return slotTableDto_to_response(slotTime,result)