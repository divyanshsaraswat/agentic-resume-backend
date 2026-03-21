from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class NotificationType(str, Enum):
    RESUME_APPROVED = "resume_approved"
    RESUME_REJECTED = "resume_rejected"
    NEW_FEEDBACK = "new_feedback"
    SYSTEM_ALERT = "system_alert"
    AI_ANALYSIS_COMPLETE = "ai_analysis_complete"
    RESUME_SUBMITTED = "resume_submitted"

class Notification(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    title: str
    description: str
    type: NotificationType
    is_read: bool = False
    metadata: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
