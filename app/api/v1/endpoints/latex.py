from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.api import deps
from app.models.user import UserInDB
from app.services.latex_service import LatexService
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
    
    # In a real app, we might want to schedule cleanup in X minutes
    # background_tasks.add_task(LatexService.cleanup_job, result["job_id"])
    
    return result
