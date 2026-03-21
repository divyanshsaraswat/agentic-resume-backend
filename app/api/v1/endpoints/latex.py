from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.api import deps
from app.models.user import UserInDB
from app.services.latex_service import LatexService
from app.services.audit_service import AuditService
from app.models.audit_log import AuditActionType, AuditLogType
from typing import Optional

router = APIRouter()

class LatexCompileRequest(BaseModel):
    latex_code: str

class LatexCompileResponse(BaseModel):
    success: bool
    job_id: Optional[str] = None
    error: Optional[str] = None
    log: Optional[str] = None
    pdf_available: bool
    pdf_url: Optional[str] = None

@router.post("/compile", response_model=LatexCompileResponse)
async def compile_latex(
    request: LatexCompileRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(deps.get_current_user)
):
    """
    Compile LaTeX code to PDF.
    """
    result = await LatexService.compile_latex(request.latex_code)
    
    await AuditService.log_action(
        actor_id=str(current_user.id),
        actor_name=current_user.name,
        actor_role=current_user.role.value,
        action=AuditActionType.LATEX_COMPILE,
        log_type=AuditLogType.LATEX,
        target="PDF Compilation",
    )
    
    # Temporary files will be cleaned up by a periodic cron job
    # to ensure they remain available for the frontend viewer.
    
    # If successful and PDF exists, provide the public URL
    if result.get("pdf_available") and result.get("job_id"):
        result["pdf_url"] = f"/public/temp_latex/{result['job_id']}/resume.pdf"
    
    return result

@router.delete("/{job_id}", response_model=bool)
async def cleanup_latex_job(
    job_id: str,
    current_user: UserInDB = Depends(deps.get_current_user)
):
    """
    Manually clean up a LaTeX compilation job's temporary files.
    """
    try:
        LatexService.cleanup_job(job_id)
        return True
    except Exception as e:
        print(f"Failed to cleanup job {job_id}: {e}")
        return False
