from server.models.DTO.reservation_dto import ReservationResponse,ReservationCreate
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
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
async def create_reservation(reservation:ReservationCreate,background_tasks:BackgroundTasks,user=Depends(authenticate_user([UserType.HIKER]))):
     # from the token and not from the body, otherwise anyone could book in someone else's name
     reservation.user_id=user.id
     return await controller.create_reservation(reservation,background_tasks)

@router.get("/{reference}",
            response_model=ReservationResponse,
            status_code=status.HTTP_200_OK)
async def get_reservation_by_reference(reference:str,user=Depends(authenticate_user([UserType.HIKER,UserType.EMPLOYEE,UserType.WARDEN]))):
     reservation=await controller.get_reservation_by_reference(reference)
     # a hiker reads only their own bookings, the hut staff reads all of them
     if user.role==UserType.Hiker and reservation.user_id!=user.id:
          raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient rights")
     return reservation

@router.get("/user/{user_id}",
            response_model=list[ReservationResponse],
            status_code=status.HTTP_200_OK)
async def get_reservation_by_user_id(user_id:int,user=Depends(authenticate_user([UserType.HIKER]))):
     if user.id!=user_id:
          raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient rights")
     return await controller.get_reservation_by_user_id(user_id)
