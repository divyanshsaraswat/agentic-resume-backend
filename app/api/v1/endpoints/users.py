from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.api import deps
from app.db.mongodb import get_database
from app.models.user import UserInDB, UserUpdate, UserRole, PyObjectId
from app.services.resume_service import ResumeService
from bson import ObjectId
from datetime import datetime

router = APIRouter()

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
    
    if current_user.role != UserRole.ADMIN and str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    
    update_data = user_in.model_dump(exclude_unset=True)
    if not current_user.is_superadmin and "role" in update_data:
        # Only superadmin can change roles
        del update_data["role"]
    
    update_data["updated_at"] = datetime.utcnow()
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    updated_user = await db.users.find_one({"_id": ObjectId(user_id)})
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
    result = await db.users.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return None
