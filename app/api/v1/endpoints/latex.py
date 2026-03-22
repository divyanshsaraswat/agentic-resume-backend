from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.api import deps
from app.models.user import UserInDB
from app.services.latex_service import LatexService
from app.services.audit_service import AuditService
from app.models.audit_log import AuditActionType, AuditLogType
from typing import Optional, Dict, Any

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

class AsyncCompileResponse(BaseModel):
    job_id: str
    queue_position: int
    eta_seconds: int


@router.post("/compile", response_model=LatexCompileResponse)
async def compile_latex(
    request: LatexCompileRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(deps.get_current_user)
):
    """
    Compile LaTeX code to PDF (synchronous — waits for result).
    Backward-compatible endpoint used by faculty validate page.
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
    
    if result.get("pdf_available") and result.get("job_id"):
        result["pdf_url"] = f"/public/temp_latex/{result['job_id']}/resume.pdf"
    
    return result


@router.post("/compile-async")
async def compile_latex_async(
    request: LatexCompileRequest,
    current_user: UserInDB = Depends(deps.get_current_user)
):
    """
    Submit a LaTeX compilation job to the queue.
    Returns immediately with job_id and queue position.
    Frontend connects to WebSocket /ws/latex/{job_id} for live updates.
    """
    submission = await LatexService.submit_job(request.latex_code)
    
    if "error" in submission and "job_id" not in submission:
        raise HTTPException(status_code=400, detail=submission["error"])
    
    await AuditService.log_action(
        actor_id=str(current_user.id),
        actor_name=current_user.name,
        actor_role=current_user.role.value,
        action=AuditActionType.LATEX_COMPILE,
        log_type=AuditLogType.LATEX,
        target="PDF Compilation (Async)",
    )
    
    return submission


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: UserInDB = Depends(deps.get_current_user)
):
    """
    Get the current status of a compilation job (polling fallback).
    """
    return LatexService.get_job_status(job_id)


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
