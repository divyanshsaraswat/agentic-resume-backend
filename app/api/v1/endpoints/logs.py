from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.api import deps
from app.models.user import UserInDB, UserRole
from app.models.audit_log import AuditLogInDB
from app.services.audit_service import AuditService
import csv
import io
from datetime import datetime

router = APIRouter()


@router.get("", response_model=List[AuditLogInDB])
async def get_logs(
    search: Optional[str] = None,
    log_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: UserInDB = Depends(deps.check_role([UserRole.ADMIN]))
) -> Any:
    """
    Retrieve audit logs. (Admin only)
    """
    return await AuditService.get_logs(
        search=search,
        log_type=log_type,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=dict)
async def get_log_stats(
    current_user: UserInDB = Depends(deps.check_role([UserRole.ADMIN]))
) -> Any:
    """
    Get audit log statistics. (Admin only)
    """
    return await AuditService.get_stats()


@router.get("/export")
async def export_logs_csv(
    search: Optional[str] = None,
    log_type: Optional[str] = None,
    current_user: UserInDB = Depends(deps.check_role([UserRole.ADMIN]))
) -> StreamingResponse:
    """
    Export audit logs as CSV. (Admin only)
    """
    logs = await AuditService.get_logs(search=search, log_type=log_type, limit=5000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Actor", "Role", "Action", "Type", "Target"])
    
    for log in logs:
        writer.writerow([
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "",
            log.actor_name,
            log.actor_role,
            log.action,
            log.log_type,
            log.target,
        ])
    
    output.seek(0)
    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
