from server.models.DTO.user_dto import UserCreateDTO, UserResponseDTO, UserLoginDTO, UserLoginResponse
from server.repositories.user_repository import UserRepository
from server.service.mapper_service import userdao_to_responsedto, loging_response, userdao_to_userdto
from server.service.auth_service import hash_password, verify_password, generate_token
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
     passHash,salt=hash_password(password=user.password)
     created= await self.repo.create_user(user,passHash=passHash,salt=salt)
     return userdao_to_responsedto(created)

    async def login_user(self, userLog:UserLoginDTO)->UserLoginDTO:
      """Login user - throws 404 if login is not succeful"""
      users= await self.repo.get_user_by_email(userLog.email)
      userDto=userdao_to_userdto(users)
      if(verify_password(userLog.password,userDto.password,userDto.salt)):
         return loging_response(generate_token(userDto))
      

