from typing import Optional
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
from server.config.config import LINK_RECOVETY_PASSWORD
from server.models.DAO.user import UserDAO
from server.models.DTO.user_dto import ChangePasswordEmail, EmailUserDTO, ResponseResetPassword, SetPasswordDTO, UserCreateDTO, UserResponseDTO, UserLoginDTO, UserLoginResponse, UserSearchResponse
from server.repositories.user_repository import UserRepository
from server.service.email_service import send_reset_password_to_user_email
from server.service.mapper_service import userdao_to_responsedto, loging_response, userdao_to_userdto,userdao_to_userdto_detail,userDAO_to_searchResponse
from server.service.auth_service import generate_token
from server.utils.security import hash_password, verify_password
from server.models.error.conflict_error import ConflictError
from server.models.error.unauthorized_error import UnauthorizedError
from server.models.error.notfound_error import NotFoundError
from server.models.enum.user_type import UserType
from server.service.auth_service import generate_token_forgot_password
from server.service.email_service import information_email

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
         if users.first_login:
            return JSONResponse(
               content={
                  "token":generate_token_forgot_password(userDto.email)
               },
               status_code=204,
               headers={"Location": "/recovery-password/setPassword"}
            )
         else:
            await self.repo.set_must_be_change(users.id,False)
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
   
   async def delete_user(self, user_id:int)->bool:
      return await self.repo.delete_user(user_id)
   
   async def reset_password(self,email:EmailUserDTO,bgt:BackgroundTasks|None):
      user:UserDAO=await self.repo.get_user_by_email(email.email)
      if user:
         try:
            jwt= generate_token_forgot_password(user.email)
            await self.repo.set_must_be_change(user.id,True)
            content=ChangePasswordEmail(
               email=user.email,
               link=LINK_RECOVETY_PASSWORD+jwt
            )
            information_email(send_reset_password_to_user_email,content,user.email,bgt)
         except Exception as e:
            await self.repo.set_must_be_change(user.id,False)
            raise(e)
         
      return ResponseResetPassword()
   
   async def set_password(self,ch_pw:SetPasswordDTO,email:str)->ResponseResetPassword:
      user:UserDAO= await self.repo.get_user_by_email(ch_pw.email)
      
      if user is None:
         raise UnauthorizedError("error during autentication")
      
      if user.email!=email:
         raise UnauthorizedError("error during autentication")

      if not user.first_login or not user.must_change_password:
         raise UnauthorizedError("error during autentication")
      
      await self.repo.set_password(user.id,hash_password(ch_pw.password))
      return ResponseResetPassword(msg="password change!")