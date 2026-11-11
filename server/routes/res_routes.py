from server.models.DTO.reservation_dto import ReservationResponse,ReservationCreate
from fastapi import APIRouter, Depends, HTTPException, status
from server.config.config import ROUTES
from server.middleware.auth_middleware import authenticate_user
from server.models.enum.user_type import UserType
from server.controllers.reservation_controller import ReservationController

router=APIRouter(prefix=ROUTES['RESERVATION'],tags=["Reservation"])
controller=ReservationController()

@router.post("", 
             response_model=ReservationResponse, 
             status_code=status.HTTP_201_CREATED,
             )
async def create_reservation(reservation:ReservationCreate,user=Depends(authenticate_user([UserType.Hiker]))):
     # from the token and not from the body, otherwise anyone could book in someone else's name
     reservation.user_id=user.id
     return await controller.create_reservation(reservation)

@router.get("/{reference}",
            response_model=ReservationResponse,
            status_code=status.HTTP_200_OK)
async def get_reservation_by_reference(reference:str):
     return await controller.get_reservation_by_reference(reference)

@router.get("/user/{user_id}",
            response_model=list[ReservationResponse],
            status_code=status.HTTP_200_OK)
async def get_reservation_by_user_id(user_id:str):
     return await controller.get_reservation_by_user_id(user_id)
