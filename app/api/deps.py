from typing import Generator, List, Optional
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from app.core.config import settings
from app.core import security
from app.db.mongodb import get_database
from app.models.user import UserInDB, UserRole
from bson import ObjectId

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False  # Allow us to handle missing token via query_token
)

async def get_current_user(
    token: Optional[str] = Depends(reusable_oauth2),
    query_token: Optional[str] = Query(None, alias="token")
) -> UserInDB:
    if not token and query_token:
        token = query_token
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = payload.get("sub")
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(token_data)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserInDB(**user)

def check_role(roles: List[UserRole]):
    async def role_checker(current_user: UserInDB = Depends(get_current_user)):
        if current_user.is_superadmin:
            return current_user
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges"
            )
        return current_user
    return role_checker
