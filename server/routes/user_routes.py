from fastapi import APIRouter,status
from server.config.config import ROUTES
from server.models.DTO.user_dto import UserResponseDTO,UserCreateDTO, UserLoginDTO,UserLoginResponse
from server.controllers.user_controller import UserController
from server.models.error.bad_request import BadRequestError

router= APIRouter(prefix=ROUTES['AUTH'], tags=["Auth"])
controller=UserController()

@router.post("/register",
    response_model=UserResponseDTO,
    status_code=status.HTTP_201_CREATED
)
async def create_user(user: UserCreateDTO):
    """
    Create a new hiker.

    - Request body: UserCreateDTO (email, password of at least 8 characters, phone, firstName, lastName; role is ignored)
    - Returns: Created user as UserResponseDTO
    - Missing or invalid fields are refused with 422 by the DTO
    - Status code: 201 Created
    """
    return await controller.create_user(user)

@router.post("/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK
)
async def login_user(user:UserLoginDTO):
  if not user.password:
    raise BadRequestError("empty password")
  if not user.username:
    raise BadRequestError("empty username")
  return await controller.login_user(user)