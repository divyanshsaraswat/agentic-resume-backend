from datetime import datetime, timezone, timedelta
from typing import Optional
from app.db.mongodb import get_database
from app.models.user import UserInDB
from app.core.config import settings
from bson import ObjectId

class CreditService:
    @staticmethod
    async def get_user_with_refilled_credits(user_id: str) -> Optional[dict]:
        """
        Fetches user and resets credits if 1 hour has passed since last refill.
        Returns the raw user document from MongoDB.
        """
        db = get_database()
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            return None
            
        last_refill = user_doc.get("last_credit_refill")
        if isinstance(last_refill, str):
            last_refill = datetime.fromisoformat(last_refill.replace('Z', '+00:00'))
        
        # Ensure last_refill is aware
        if last_refill and last_refill.tzinfo is None:
            last_refill = last_refill.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        
        # If 1 hour has passed, refill credits to 20
        if not last_refill or (now - last_refill) >= timedelta(hours=1):
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "llm_credits": settings.LLM_CREDITS_PER_HOUR,
                        "last_credit_refill": now
                    }
                }
            )
            user_doc["llm_credits"] = settings.LLM_CREDITS_PER_HOUR
            user_doc["last_credit_refill"] = now
            
        return user_doc

    @staticmethod
    async def consume_credits(user_id: str, model_name: str) -> bool:
        """
        Deducts credits based on model name. 
        Returns True if successful, False if insufficient credits.
        """
        db = get_database()
        user_doc = await CreditService.get_user_with_refilled_credits(user_id)
        if not user_doc:
            return False
            
        # Get credit cost for model
        cost = settings.MODEL_CREDIT_COSTS.get(model_name, 1) # Default to 1 if not found
        
        current_credits = user_doc.get("llm_credits", 0)
        
        if current_credits < cost:
            return False
            
        # Deduct credits
        result = await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"llm_credits": -cost}}
        )
        
        return result.modified_count > 0

    @staticmethod
    async def get_credit_info(user_id: str) -> dict:
        """
        Returns current credits and time remaining until next refill.
        """
        user_doc = await CreditService.get_user_with_refilled_credits(user_id)
        if not user_doc:
            return {"credits": 0, "next_refill_in_minutes": 0}
            
        last_refill = user_doc.get("last_credit_refill")
        if isinstance(last_refill, str):
            last_refill = datetime.fromisoformat(last_refill.replace('Z', '+00:00'))
            
        if last_refill and last_refill.tzinfo is None:
            last_refill = last_refill.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        next_refill = last_refill + timedelta(hours=1)
        remaining = max(0, int((next_refill - now).total_seconds() / 60))
        
        return {
            "credits": user_doc.get("llm_credits", 0),
            "next_refill_in_minutes": remaining,
            "preferred_model": user_doc.get("preferred_model") or settings.DEFAULT_MODEL
        }
