from fastapi import APIRouter, Depends, HTTPException, Query, status
from server.models.DTO.slot_dto import SlotResponse,SlotCreation
from server.middleware.auth_middleware import authenticate_user
from server.models.enum.user_type import UserType
from server.config.config import ROUTES
from server.controllers.slot_controller import SlotController
from server.models.DTO.slot_dto import SlotDetail
from server.models.DTO.reservation_dto import SlotAvailabilityResponse
from server.models.DTO.table_dto import TableResponse
from server.models.DTO.time_dto import TimeResponse
from datetime import date, time
from typing import Optional

router=APIRouter(prefix=ROUTES['SLOT'],tags=["SLOT"])
controller=SlotController()
@router.post("",
             response_model=SlotResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(authenticate_user([UserType.EMPLOYEE,UserType.WARDEN]))]
             )
async def setUpSlot(slot: SlotCreation):
    return await controller.setUpSlot(slot)

@router.get("",
            response_model=list[SlotDetail],
            status_code=status.HTTP_200_OK,
            dependencies=[Depends(authenticate_user([UserType.HIKER,UserType.EMPLOYEE,UserType.WARDEN]))])
async def getSlotTime(date:Optional[date]=None):
    return await controller.getSlotTime(date)

@router.get("/availability",
            response_model=list[SlotAvailabilityResponse],
            status_code=status.HTTP_200_OK)
async def getSlotAvailabilityByDateTime(
    date: Optional[date]=Query(None),
    time: Optional[time]=Query(None),
    party_size: Optional[int] = Query(None, ge=1, description="Party size to check availability and table layout for"),
):
    """Check table availability by date, time, and party size without login (MH-04)."""
    return await controller.getSlotAvailabilityByDateTime(date, time, party_size)

@router.get("/{slot_id}/availability",
            response_model=SlotAvailabilityResponse,
            status_code=status.HTTP_200_OK)
async def getSlotAvailability(
    slot_id: int,
    party_size: Optional[int] = Query(None, ge=1, description="Party size to check availability and table layout for"),
    partySize: Optional[int] = Query(None, ge=1, description="Party size alias (camelCase)"),
):
    """Retrieve slot capacity, real-time availability, and table layout breakdown (MH-04)."""
    p_size = party_size if party_size is not None else partySize
    return await controller.getSlotAvailability(slot_id, p_size)

@router.get("/times",
            response_model=list[TimeResponse],
            status_code=status.HTTP_200_OK,
            dependencies=[Depends(authenticate_user([UserType.EMPLOYEE,UserType.WARDEN]))])
async def get_list_time():
    return await controller.get_list_time()

@router.get("/tables",
            response_model=list[TableResponse],
            status_code=status.HTTP_200_OK,
            dependencies=[Depends(authenticate_user([UserType.EMPLOYEE,UserType.WARDEN]))])
async def get_list_time():
    return await controller.get_list_table()
