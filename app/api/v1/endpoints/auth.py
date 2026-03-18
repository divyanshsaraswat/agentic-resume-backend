from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from google.oauth2 import id_token
from google.auth.transport import requests
from app.core import security
from app.core.config import settings
from app.api import deps
from app.db.mongodb import get_database
from app.models.user import UserInDB, UserCreate, UserRole, UserBase
from app.services.audit_service import AuditService
from app.models.audit_log import AuditActionType, AuditLogType
from datetime import datetime

router = APIRouter()

@router.post("/login/google")
async def login_google(token: str):
    try:
        # Specify the GOOGLE_CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        email = idinfo['email']
        name = idinfo.get('name', '')

        # MNIT check
        if not email.endswith("@mnit.ac.in"):
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only @mnit.ac.in emails are allowed",
            )

        db = get_database()
        user = await db.users.find_one({"email": email})
        
        user_role = "student"
        if not user:
            # Create user if not exists
            new_user = UserInDB(
                name=name,
                email=email,
                role=UserRole.STUDENT, # Default role
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            result = await db.users.insert_one(new_user.model_dump(by_alias=True))
            user_id = str(result.inserted_id)
        else:
            user_id = str(user["_id"])
            user_role = user.get("role", "student")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            user_id, expires_delta=access_token_expires
        )
        
        await AuditService.log_action(
            actor_id=user_id,
            actor_name=name or email,
            actor_role=user_role,
            action=AuditActionType.LOGIN_SUCCESS,
            log_type=AuditLogType.AUTH,
            target=email,
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
    except ValueError:
        # Invalid token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(deps.get_current_user)):
    return current_user
