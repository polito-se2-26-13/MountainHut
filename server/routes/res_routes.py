from server.models.DTO.reservation_dto import ReservationResponse,ReservationCreate,ReservationUpdate
from server.models.DAO.reservation import ReservationDAO
from server.database import get_db
from server.service.email_service import format_booking_email_html, format_booking_email_text
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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

@router.get("/reference/{reference}",
            response_model=ReservationResponse,
            status_code=status.HTTP_200_OK)
async def get_reservation_by_reference(reference:str,user=Depends(authenticate_user([UserType.HIKER,UserType.EMPLOYEE,UserType.WARDEN]))):
     reservation=await controller.get_reservation_by_reference(reference,user.id,user.role)
     # a hiker reads only their own bookings, the hut staff reads all of them
     return reservation

@router.get("/{reference}/email-preview", status_code=status.HTTP_200_OK)
async def get_email_preview(reference: str, db: AsyncSession = Depends(get_db)):
     result = await db.execute(select(ReservationDAO).where(ReservationDAO.booking_reference == reference))
     reservation = result.scalar_one_or_none()
     if not reservation:
          raise HTTPException(status_code=404, detail="booking reference not found")
     return {
          "booking_reference": reservation.booking_reference,
          "recipient_email": reservation.contact_email,
          "subject": f"Mountain Hut Booking Confirmation [{reservation.booking_reference}]",
          "email_text": format_booking_email_text(reservation),
          "email_html": format_booking_email_html(reservation),
     }

@router.get("/user",
            response_model=list[ReservationResponse],
            status_code=status.HTTP_200_OK)
async def get_reservation_by_user_id(user=Depends(authenticate_user([UserType.HIKER]))):
     return await controller.get_reservation_by_user_id(user.id)

@router.patch("/reference/{reference}",
              response_model=ReservationResponse,
              status_code=status.HTTP_200_OK)
async def update_reservation(
     reference: str,
     changes: ReservationUpdate,
     background_tasks: BackgroundTasks,
     user=Depends(authenticate_user([UserType.HIKER])),
):
     return await controller.update_reservation(reference, user.id, changes, background_tasks)
