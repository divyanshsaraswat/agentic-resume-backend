from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.api import deps
from app.db.mongodb import get_database
from app.models.user import UserInDB, UserUpdate, UserRole, PyObjectId
from bson import ObjectId
from datetime import datetime

router = APIRouter()

@router.get("", response_model=List[UserInDB])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: UserInDB = Depends(deps.check_role([UserRole.ADMIN]))
) -> Any:
    """
    Retrieve users. (Admin only)
    """
    db = get_database()
    users = await db.users.find().skip(skip).limit(limit).to_list(length=limit)
    return [UserInDB(**user) for user in users]

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
