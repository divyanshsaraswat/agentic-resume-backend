from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime, timezone
from enum import Enum
from app.models.user import PyObjectId


class AuditActionType(str, Enum):
    # Auth
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    
    # Resume
    RESUME_CREATED = "RESUME_CREATED"
    RESUME_UPDATED = "RESUME_UPDATED"
    RESUME_DELETED = "RESUME_DELETED"
    RESUME_SUBMITTED = "RESUME_SUBMITTED"
    VERSION_ADDED = "VERSION_ADDED"
    
    # Validation
    RESUME_APPROVED = "RESUME_APPROVED"
    RESUME_REJECTED = "RESUME_REJECTED"
    
    # User management
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DELETED = "USER_DELETED"
    ROLE_CHANGED = "ROLE_CHANGED"
    STATUS_TOGGLED = "STATUS_TOGGLED"

    # AI Operations
    AI_IMPROVE_BULLET = "AI_IMPROVE_BULLET"
    AI_GENERATE_SECTION = "AI_GENERATE_SECTION"
    AI_SCORE_RESUME = "AI_SCORE_RESUME"
    AI_CHAT = "AI_CHAT"

    # LaTeX Operations
    LATEX_COMPILE = "LATEX_COMPILE"


class AuditLogType(str, Enum):
    AUTH = "auth"
    RESUME = "resume"
    VALIDATION = "validation"
    USER = "user"
    AI = "ai"
    LATEX = "latex"


class AuditLogCreate(BaseModel):
    actor_id: str
    actor_name: str
    actor_role: str
    action: AuditActionType
    log_type: AuditLogType
    target: str = ""
    metadata: dict = {}


class AuditLogInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    actor_id: str
    actor_name: str
    actor_role: str
    action: str
    log_type: str
    target: str = ""
    metadata: dict = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
