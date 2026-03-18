from datetime import datetime, timezone
from typing import Optional, List
from app.db.mongodb import get_database
from app.models.audit_log import AuditLogCreate, AuditLogInDB, AuditActionType, AuditLogType


class AuditService:
    """Service for recording and querying audit trail events."""
    
    @staticmethod
    async def log_action(
        actor_id: str,
        actor_name: str,
        actor_role: str,
        action: AuditActionType,
        log_type: AuditLogType,
        target: str = "",
        metadata: dict = {}
    ) -> None:
        """Record an audit event. Fire-and-forget — never raises."""
        try:
            db = get_database()
            log_entry = {
                "actor_id": actor_id,
                "actor_name": actor_name,
                "actor_role": actor_role,
                "action": action.value,
                "log_type": log_type.value,
                "target": target,
                "metadata": metadata,
                "timestamp": datetime.now(timezone.utc),
            }
            await db.audit_logs.insert_one(log_entry)
        except Exception as e:
            # Audit logging should never block the main operation
            print(f"[AuditService] Failed to log action: {e}")
    
    @staticmethod
    async def get_logs(
        search: Optional[str] = None,
        log_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLogInDB]:
        """Retrieve audit logs with optional filtering."""
        db = get_database()
        query: dict = {}
        
        if log_type:
            query["log_type"] = log_type
        
        if search:
            query["$or"] = [
                {"actor_name": {"$regex": search, "$options": "i"}},
                {"action": {"$regex": search, "$options": "i"}},
                {"target": {"$regex": search, "$options": "i"}},
            ]
        
        cursor = db.audit_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        logs = await cursor.to_list(length=limit)
        return [AuditLogInDB(**log) for log in logs]
    
    @staticmethod
    async def get_stats() -> dict:
        """Get audit log statistics."""
        db = get_database()
        total = await db.audit_logs.count_documents({})
        
        # Get action counts using aggregation
        pipeline = [
            {"$group": {"_id": "$action", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]
        top_action_result = await db.audit_logs.aggregate(pipeline).to_list(length=1)
        top_action = top_action_result[0]["_id"] if top_action_result else "N/A"
        
        # Count by type
        type_pipeline = [
            {"$group": {"_id": "$log_type", "count": {"$sum": 1}}}
        ]
        type_counts = await db.audit_logs.aggregate(type_pipeline).to_list(length=10)
        type_map = {item["_id"]: item["count"] for item in type_counts}
        
        return {
            "total_events": total,
            "top_action": top_action,
            "by_type": type_map,
        }
