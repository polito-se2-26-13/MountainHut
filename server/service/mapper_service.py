from server.models.DTO.error_dto import ErrorDTO
from server.models.DTO.user_dto import UserResponseDTO,UserLoginResponse,UserDTO
from server.models.DAO.user_dao import UserDAO

def create_error_dto(code: int, message: str, name: str) -> ErrorDTO:
    """Create an ErrorDTO instance"""
    return ErrorDTO(code=code, message=message, name=name)

def userdao_to_responsedto(userDao:UserDAO)->UserResponseDTO:
    return UserResponseDTO(
        id=userDao.id
    )

def loging_response(token:str)->UserLoginResponse:
    return UserLoginResponse(token=token)

def userdao_to_userdto(user:UserDAO)->UserDTO:
    return UserDTO(
        email=user.email,
        password=user.password,
        role=user.role,
        salt=user.salt,
        name=user.name,
        surname=user.surname,
        phone=user.phone
    )