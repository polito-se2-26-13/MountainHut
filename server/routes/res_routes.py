from server.models.DTO.reservation_dto import ReservationResponse,ReservationCreate
from fastapi import APIRouter, Depends, HTTPException, status
from server.config.config import ROUTES
from server.middleware.auth_middleware import authenticate_user
from server.models.enum.user_type import UserType
from server.controllers.reservation_controller import ReservationController

router=APIRouter(prefix=ROUTES['RESERVATION'],tags=["Reservation"])
controller=ReservationController()

@router.post("/", 
             response_model=ReservationResponse, 
             status_code=status.HTTP_201_CREATED,
             #dependencies=[Depends(authenticate_user([user.value for user in UserType]))],
             )
async def create_reservation(reservation:ReservationCreate):
     return await controller.create_reservation(reservation)