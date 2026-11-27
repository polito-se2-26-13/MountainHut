from fastapi import  HTTPException, Header, status
from typing import Optional, List
from fastapi import Depends
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from server.service.auth_service import process_token,process_token_forgot_password
from server.models.enum.user_type import UserType
from server.models.error.unauthorized_error import UnauthorizedError
security = HTTPBearer()

def authenticate_user(allowed_roles: List[UserType]):
    async def _dep(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        authorization = f"{credentials.scheme} {credentials.credentials}"

        return await process_token(authorization, allowed_roles)

    return _dep

def authenticate_forgot_password():
    async def _dep(
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            authorization = f"{credentials.scheme} {credentials.credentials}"
    
            return await process_token_forgot_password(authorization)
    
    return _dep