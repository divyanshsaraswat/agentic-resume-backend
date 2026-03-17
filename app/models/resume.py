from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
from bson import ObjectId
from app.models.user import PyObjectId

class ResumeStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"

class ResumeVersion(BaseModel):
    version_id: PyObjectId = Field(default_factory=PyObjectId)
    type: str # e.g., "SDE", "Core"
    file_url: Optional[str] = None
    latex_code: str
    parsed_data: dict = {}
    ai_score: dict = {}
    status: ResumeStatus = ResumeStatus.DRAFT
    submitted_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ResumeCreate(BaseModel):
    initial_latex: str
    type: str

class ResumeInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    versions: List[ResumeVersion] = []
    default_version_id: Optional[PyObjectId] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
