from typing import Optional
from server.models.DTO.user_dto import UserCreateDTO, UserResponseDTO, UserLoginDTO, UserLoginResponse, UserSearchResponse
from server.repositories.user_repository import UserRepository
from server.service.mapper_service import userdao_to_responsedto, loging_response, userdao_to_userdto,userdao_to_userdto_detail,userDAO_to_searchResponse
from server.service.auth_service import generate_token
from server.utils.security import hash_password, verify_password
from server.models.error.conflict_error import ConflictError
from server.models.error.unauthorized_error import UnauthorizedError
from server.models.error.notfound_error import NotFoundError
from server.models.enum.user_type import UserType

class UserController():
   def __init__(self):
          self.repo= UserRepository()

   async def create_user(self,user:UserCreateDTO) -> UserResponseDTO:
     """Create a hiker - throws ConflictError if the email exists"""
     # only hikers register themselves, the staff accounts are the sample ones for now
     user.role=UserType.HIKER
     # one account per email, whatever capitals it is written with
     user.email=user.email.lower()
     users= await self.repo.get_user_by_email(user.email)
     if users:
      raise ConflictError(f"exist a user with email {user.email}")
     created= await self.repo.create_user(user,passHash=hash_password(user.password))
     return userdao_to_responsedto(created)

   async def login_user(self, userLog:UserLoginDTO)->UserLoginDTO:
      """Login user - throws 401 if email or password are wrong"""
      users= await self.repo.get_user_by_email(userLog.username)
      if users is None:
         raise UnauthorizedError("email or password wrong")
      userDto=userdao_to_userdto(users)
      if(verify_password(userLog.password,userDto.password)):
         return loging_response(generate_token(userDto),userdao_to_userdto_detail(users))
      else:
         raise UnauthorizedError("email or password wrong")

   async def find_user(self,name:Optional[str]=None,mail:Optional[str]=None,phone:Optional[str]=None)->list[UserSearchResponse]:
      list=await self.repo.get_user_by_field_hiker(name,mail,phone)
      if not list:
         raise NotFoundError("no user found")
      resp=[]
      for l in list:
         resp.append(userDAO_to_searchResponse(l))
      return resp