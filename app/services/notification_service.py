from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from app.db.mongodb import get_database
from app.models.notification import Notification, NotificationType

class NotificationService:
    @staticmethod
    async def create_notification(
        user_id: str,
        title: str,
        description: str,
        n_type: NotificationType
    ) -> str:
        db = get_database()
        notification = Notification(
            user_id=user_id,
            title=title,
            description=description,
            type=n_type
        )
        
        # Convert to dict for MongoDB
        notification_dict = notification.model_dump(by_alias=True, exclude={"id"})
        result = await db.notifications.insert_one(notification_dict)
        return str(result.inserted_id)

    @staticmethod
    async def get_user_notifications(user_id: str, limit: int = 20) -> List[dict]:
        db = get_database()
        cursor = db.notifications.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        notifications = await cursor.to_list(length=limit)
        
        # Convert ObjectId and datetime to serializable format
        for n in notifications:
            n["_id"] = str(n["_id"])
            if "created_at" in n and isinstance(n["created_at"], datetime):
                n["created_at"] = n["created_at"].isoformat()
        
        return notifications

    @staticmethod
    async def mark_as_read(notification_id: str) -> bool:
        db = get_database()
        result = await db.notifications.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"is_read": True}}
        )
        return result.modified_count > 0

    @staticmethod
    async def mark_all_as_read(user_id: str) -> int:
        db = get_database()
        result = await db.notifications.update_many(
            {"user_id": user_id, "is_read": False},
            {"$set": {"is_read": True}}
        )
        return result.modified_count

    @staticmethod
    async def get_unread_count(user_id: str) -> int:
        db = get_database()
        return await db.notifications.count_documents({"user_id": user_id, "is_read": False})
