from fastapi import APIRouter, Depends, HTTPException, status
from server.models.DTO.slot_dto import SlotResponse,SlotCreation
from server.middleware.auth_middleware import authenticate_user
from server.models.enum.user_type import UserType
from server.config.config import ROUTES
from server.controllers.slot_controller import SlotController
from server.models.DTO.slot_dto import SlotDetail
from server.models.DTO.reservation_dto import SlotAvailabilityResponse
from datetime import date
from typing import Optional

router=APIRouter(prefix=ROUTES['SLOT'],tags=["SLOT"])
controller=SlotController()
@router.post("",
             response_model=SlotResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(authenticate_user([UserType.Employee,UserType.Warden]))]
             )
async def setUpSlot(slot: SlotCreation):
    return await controller.setUpSlot(slot)

@router.get("",
            response_model=list[SlotDetail],
            status_code=status.HTTP_200_OK,
            dependencies=[Depends(authenticate_user([UserType.Hiker,UserType.Employee,UserType.Warden]))])
async def getSlotTime(date:Optional[date]=None):
    return await controller.getSlotTime(date)

@router.get("/{slot_id}/availability",
            response_model=SlotAvailabilityResponse,
            status_code=status.HTTP_200_OK)
async def getSlotAvailability(slot_id:int):
    return await controller.getSlotAvailability(slot_id)