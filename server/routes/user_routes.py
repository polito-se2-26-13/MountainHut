from fastapi import APIRouter,status,Query,Depends
from typing import Optional
from server.config.config import ROUTES
from server.middleware.auth_middleware import authenticate_user
from server.models.DTO.user_dto import UserSearchResponse
from server.controllers.user_controller import UserController
from server.models.error.bad_request import BadRequestError
from server.models.enum.user_type import UserType

router= APIRouter(prefix=ROUTES['USER'], tags=["User"])
controller=UserController()

@router.get("/find",
    response_model=list[UserSearchResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(authenticate_user([UserType.EMPLOYEE,UserType.WARDEN]))]
)
async def create_user(
    name: Optional[str]=Query(None),
    email: Optional[str]=Query(None),
    phone: Optional[str]=Query(None),):
    if name is None and email is None and phone is None:
        raise BadRequestError("one field must be not empty")
    return await controller.find_user(name,email,phone)