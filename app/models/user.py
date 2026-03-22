from pydantic import BaseModel, Field, EmailStr, ConfigDict, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import core_schema
from typing import Optional, List, Any
from datetime import datetime, timezone
from enum import Enum
from bson import ObjectId
from pydantic import model_validator
from app.core.utils import derive_student_data

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ]),
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x), when_used="json"
            ),
        )

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> Any:
        return handler(core_schema.str_schema())

class UserRole(str, Enum):
    ADMIN = "admin"
    FACULTY = "faculty"
    SPC = "spc"
    STUDENT = "student"

class UserBase(BaseModel):
    name: str
    email: EmailStr
    picture: Optional[str] = None
    role: UserRole = UserRole.STUDENT
    is_superadmin: bool = False
    is_active: bool = True
    department: Optional[str] = None
    year: Optional[int] = None
    storage_limit_mb: int = 20
    storage_used_bytes: int = 0
    llm_credits: int = 20
    preferred_model: Optional[str] = None
    notifications_enabled: bool = True

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    is_superadmin: Optional[bool] = None
    is_active: Optional[bool] = None
    department: Optional[str] = None
    year: Optional[int] = None
    preferred_model: Optional[str] = None
    notifications_enabled: Optional[bool] = None

class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    notifications: List[dict] = []
    last_credit_refill: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode='after')
    def apply_student_derivation(self) -> 'UserInDB':
        if self.role == UserRole.STUDENT:
            derived = derive_student_data(self.email)
            if derived:
                if not self.department or self.department == "Not Assigned":
                    self.department = derived.get("department") or self.department
                if not self.year:
                    self.year = derived.get("year") or self.year
        return self

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
