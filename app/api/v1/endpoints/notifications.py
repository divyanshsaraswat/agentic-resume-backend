import asyncio
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.api import deps
from app.models.user import UserInDB
from app.services.notification_service import NotificationService
from app.services.notification_manager import notifier

router = APIRouter()

@router.get("/stream")
async def stream_notifications(
    current_user: UserInDB = Depends(deps.get_current_user)
):
    """
    SSE stream for real-time notification triggers.
    """
    return StreamingResponse(
        notifier.subscribe(str(current_user.id)),
        media_type="text/event-stream"
    )

@router.get("", response_model=List[dict])
async def get_notifications(
    current_user: UserInDB = Depends(deps.get_current_user),
    limit: int = Query(20, ge=1, le=100)
) -> Any:
    """
    Retrieve current user's notifications.
    """
    return await NotificationService.get_user_notifications(str(current_user.id), limit)

@router.get("/unread-count")
async def get_unread_count(
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Get unread notification count.
    """
    count = await NotificationService.get_unread_count(str(current_user.id))
    return {"count": count}

@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Mark a specific notification as read.
    """
    success = await NotificationService.mark_as_read(str(current_user.id), notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "success"}

@router.put("/mark-all-read")
async def mark_all_as_read(
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Mark all notifications for the current user as read.
    """
    count = await NotificationService.mark_all_as_read(str(current_user.id))
    return {"status": "success", "count": count}
