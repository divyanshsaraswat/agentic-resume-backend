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

class ResumeFormat(str, Enum):
    LATEX = "latex"
    PDF = "pdf"
    DOCX = "docx"

class ResumeVersion(BaseModel):
    version_id: PyObjectId = Field(default_factory=PyObjectId)
    type: str # e.g., "SDE", "Core"
    format: ResumeFormat = ResumeFormat.LATEX
    file_url: Optional[str] = None
    latex_code: str = ""
    parsed_data: dict = {}
    ai_score: dict = {}
    status: ResumeStatus = ResumeStatus.DRAFT
    reviewer_remark: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewer_picture_url: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ResumeCreate(BaseModel):
    initial_latex: Optional[str] = ""
    file_url: Optional[str] = None
    type: str
    format: ResumeFormat = ResumeFormat.LATEX

class ReviewHistoryEntry(BaseModel):
    version_id: PyObjectId
    reviewer_name: str
    reviewer_picture_url: Optional[str] = None
    status: ResumeStatus
    remark: Optional[str] = None
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ResumeInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    versions: List[ResumeVersion] = []
    review_history: List[ReviewHistoryEntry] = []
    default_version_id: Optional[PyObjectId] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
