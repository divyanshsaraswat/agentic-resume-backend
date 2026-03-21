from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from app.db.mongodb import get_database
from app.models.notification import Notification, NotificationType
from app.services.notification_manager import notifier

class NotificationService:
    @staticmethod
    async def create_notification(
        user_id: str,
        title: str,
        description: str,
        n_type: NotificationType,
        metadata: Optional[dict] = None
    ) -> str:
        db = get_database()
        notification_id = str(ObjectId())
        notification = {
            "_id": notification_id,
            "title": title,
            "description": description,
            "type": n_type.value if hasattr(n_type, 'value') else n_type,
            "is_read": False,
            "metadata": metadata,
            "created_at": datetime.now()
        }
        
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {
                "notifications": {
                    "$each": [notification],
                    "$position": 0,
                    "$slice": 50  # Keep last 50 notifications
                }
            }}
        )
        
        # Trigger real-time update
        await notifier.notify(user_id)
        
        return notification_id

    @staticmethod
    async def get_user_notifications(user_id: str, limit: int = 20) -> List[dict]:
        db = get_database()
        user = await db.users.find_one(
            {"_id": ObjectId(user_id)},
            {"notifications": {"$slice": limit}}
        )
        if not user or "notifications" not in user:
            return []
            
        notifications = user["notifications"]
        
        # Convert datetime to serializable format (already strings or formatted as needed)
        for n in notifications:
            if "created_at" in n and isinstance(n["created_at"], datetime):
                n["created_at"] = n["created_at"].isoformat()
        
        return notifications

    @staticmethod
    async def mark_as_read(user_id: str, notification_id: str) -> bool:
        db = get_database()
        result = await db.users.update_one(
            {"_id": ObjectId(user_id), "notifications._id": notification_id},
            {"$set": {"notifications.$.is_read": True}}
        )
        return result.modified_count > 0

    @staticmethod
    async def mark_all_as_read(user_id: str) -> bool:
        db = get_database()
        # MongoDB doesn't easily update all elements in an array with positional operator
        # but we can use $[element] with arrayFilters
        result = await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"notifications.$[elem].is_read": True}},
            array_filters=[{"elem.is_read": False}]
        )
        return result.modified_count > 0

    @staticmethod
    async def get_unread_count(user_id: str) -> int:
        db = get_database()
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user or "notifications" not in user:
            return 0
        return sum(1 for n in user["notifications"] if not n.get("is_read", False))
