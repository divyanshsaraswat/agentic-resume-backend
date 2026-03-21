from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.api import deps
from app.db.mongodb import get_database
from app.models.user import UserInDB, UserCreate, UserUpdate, UserRole, PyObjectId
from app.services.resume_service import ResumeService
from app.services.audit_service import AuditService
from app.models.audit_log import AuditActionType, AuditLogType
from bson import ObjectId
from datetime import datetime, timezone

router = APIRouter()

@router.post("", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    current_user: UserInDB = Depends(deps.check_role([UserRole.ADMIN]))
) -> Any:
    """
    Create a new user. (Admin only)
    """
    db = get_database()
    
    # Validate institutional email
    if not user_in.email.endswith("@mnit.ac.in"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only @mnit.ac.in email addresses are allowed"
        )
    
    existing = await db.users.find_one({"email": user_in.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    
    user_data = user_in.model_dump()
    user_data["created_at"] = datetime.now(timezone.utc)
    user_data["updated_at"] = datetime.now(timezone.utc)
    user_data["assigned_students"] = []
    
    result = await db.users.insert_one(user_data)
    created_user = await db.users.find_one({"_id": result.inserted_id})
    
    await AuditService.log_action(
        actor_id=str(current_user.id),
        actor_name=current_user.name,
        actor_role=current_user.role.value,
        action=AuditActionType.USER_CREATED,
        log_type=AuditLogType.USER,
        target=f"{user_in.name} ({user_in.email})",
        metadata={"new_role": user_in.role.value}
    )
    
    return UserInDB(**created_user)

@router.get("", response_model=List[UserInDB])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None,
    current_user: UserInDB = Depends(deps.check_role([UserRole.ADMIN]))
) -> Any:
    """
    Retrieve users. (Admin only)
    """
    db = get_database()
    query = {}
    if role:
        query["role"] = role
    users = await db.users.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [UserInDB(**user) for user in users]

@router.get("/stats", response_model=dict)
async def get_admin_stats(
    current_user: UserInDB = Depends(deps.check_role([UserRole.ADMIN]))
) -> Any:
    """
    Get statistics for the admin dashboard. (Admin only)
    """
    return await ResumeService.get_admin_dashboard_stats()

@router.get("/students", response_model=List[dict])
async def read_students(
    search: Optional[str] = None,
    year: Optional[List[int]] = Query(None),
    department: Optional[List[str]] = Query(None),
    current_user: UserInDB = Depends(deps.check_role([UserRole.ADMIN, UserRole.SPC]))
) -> Any:
    """
    Retrieve students tracking list. (Admin/SPC only)
    """
    return await ResumeService.get_students_list(
        search=search,
        years=year,
        departments=department
    )

@router.get("/students/analytics", response_model=dict)
async def get_student_analytics(
    current_user: UserInDB = Depends(deps.check_role([UserRole.ADMIN, UserRole.SPC]))
) -> Any:
    """
    Get aggregate student placement analytics. (Admin only)
    """
    return await ResumeService.get_student_analytics()

@router.get("/{user_id}", response_model=UserInDB)
async def read_user_by_id(
    user_id: str,
    current_user: UserInDB = Depends(deps.get_current_user),
) -> Any:
    """
    Get a specific user by id.
    """
    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if current_user.role != UserRole.ADMIN and str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return UserInDB(**user)

@router.patch("/{user_id}", response_model=UserInDB)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    current_user: UserInDB = Depends(deps.get_current_user),
) -> Any:
    """
    Update a user.
    """
    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Allow if user is Admin, Superadmin, or updating themselves
    is_admin = current_user.role == UserRole.ADMIN
    is_self = str(current_user.id) == user_id
    
    if not (is_admin or current_user.is_superadmin or is_self):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    
    update_data = user_in.model_dump(exclude_unset=True)
    
    # Strictly prevent editing personal profile fields in sync with Google Auth
    for forbidden in ["name", "email", "picture"]:
        if forbidden in update_data:
            del update_data[forbidden]

    if not current_user.is_superadmin and "role" in update_data:
        # Only superadmin can change roles
        del update_data["role"]
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    updated_user = await db.users.find_one({"_id": ObjectId(user_id)})
    
    # Determine specific audit action
    if "role" in update_data:
        audit_action = AuditActionType.ROLE_CHANGED
    elif "is_active" in update_data:
        audit_action = AuditActionType.STATUS_TOGGLED
    else:
        audit_action = AuditActionType.USER_UPDATED
    
    await AuditService.log_action(
        actor_id=str(current_user.id),
        actor_name=current_user.name,
        actor_role=current_user.role.value,
        action=audit_action,
        log_type=AuditLogType.USER,
        target=f"{user['name']} ({user['email']})",
        metadata=update_data
    )
    
    return UserInDB(**updated_user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: UserInDB = Depends(deps.check_role([UserRole.ADMIN]))
) -> None:
    """
    Delete a user. (Admin only)
    """
    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    result = await db.users.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    await AuditService.log_action(
        actor_id=str(current_user.id),
        actor_name=current_user.name,
        actor_role=current_user.role.value,
        action=AuditActionType.USER_DELETED,
        log_type=AuditLogType.USER,
        target=f"{user['name']} ({user['email']})" if user else user_id,
    )
    
    return None

@router.get("/llm/models-info", response_model=dict)
async def get_llm_models_info(
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Get available LLM models and their credit costs.
    """
    from app.core.config import settings
    return {
        "models": settings.MODEL_CREDIT_COSTS,
        "default": settings.DEFAULT_MODEL,
        "hourly_limit": settings.LLM_CREDITS_PER_HOUR
    }

