from server.models.DTO.user_dto import UserCreateDTO, UserResponseDTO, UserLoginDTO, UserLoginResponse
from server.repositories.user_repository import UserRepository
from server.service.mapper_service import userdao_to_responsedto, loging_response, userdao_to_userdto,userdao_to_userdto_detail
from server.service.auth_service import generate_token
from server.utils.security import hash_password, verify_password
from server.models.error.conflict_error import ConflictError
from server.models.error.notfound_error import NotFoundError

class UserController():
    def __init__(self):
          self.repo= UserRepository()

    async def create_user(self,user:UserCreateDTO) -> UserResponseDTO:
     """Create user - throws ConflictError if username exists"""
     users= await self.repo.get_user_by_email(user.email)
     if users:
      raise ConflictError(f"exist a user with email {user.email}")
     created= await self.repo.create_user(user,passHash=hash_password(user.password))
     return userdao_to_responsedto(created)

    async def login_user(self, userLog:UserLoginDTO)->UserLoginDTO:
      """Login user - throws 404 if login is not succeful"""
      users= await self.repo.get_user_by_email(userLog.username)
      if users is None:
         raise NotFoundError("email or password wrong")
      userDto=userdao_to_userdto(users)
      if(verify_password(userLog.password,userDto.password)):
         return loging_response(generate_token(userDto),userdao_to_userdto_detail(users))
      else:
         raise NotFoundError("email or password wrong")


