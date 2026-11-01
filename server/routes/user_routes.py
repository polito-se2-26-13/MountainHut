from fastapi import APIRouter,status
from server.config.config import ROUTES
from server.models.DTO.user_dto import UserResponseDTO,UserCreateDTO, UserLoginDTO,UserLoginResponse
from server.controllers.user_controller import UserController
from server.models.error.bad_request import BadRequestError

router= APIRouter(prefix=ROUTES['AUTH'], tags=["Auth"])
controller=UserController()

@router.post("/singup",
    response_model=UserResponseDTO, 
    status_code=status.HTTP_201_CREATED
)
async def create_user(user: UserCreateDTO):
    """
    Create a new user.

    - Request body: UserCreateDTO (contains email, password, role, phone, name, surname)
    - Returns: Created user as UserResponseDTO
    - Raises:
      - BadRequestError: when mandatory fields (password, type) are missing or invalid
    - Status code: 201 Created
    """
    if not user.password:
      raise BadRequestError("empty password")
    if not user.email :
        raise BadRequestError("empty email")
    if not user.name:
        raise BadRequestError("empty name")
    if not user.surname :
      raise BadRequestError("empty surname")
    if not user.role:
        raise BadRequestError("empty role")
    return await controller.create_user(user)

@router.post("/login",
    response_model=UserLoginResponse, 
    status_code=status.HTTP_201_CREATED
)
async def login_user(user:UserLoginDTO):
  if not user.password:
    raise BadRequestError("empty password")
  if not user.email:
    raise BadRequestError("empty email")
  return await controller.login_user(user)