from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.api import deps
from app.models.user import UserInDB
from app.services.ai_service import AIService

router = APIRouter()

class ImproveBulletRequest(BaseModel):
    bullet: str

class GenerateSectionRequest(BaseModel):
    section_name: str
    user_context: str

class ScoreResumeRequest(BaseModel):
    resume_text: str

@router.post("/improve-bullet")
async def improve_bullet(
    request: ImproveBulletRequest,
    current_user: UserInDB = Depends(deps.get_current_user)
):
    """
    Improve a resume bullet point using AI.
    """
    try:
        refined_text = await AIService.improve_bullet(request.bullet)
        return {"original": request.bullet, "improved": refined_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-section")
async def generate_section(
    request: GenerateSectionRequest,
    current_user: UserInDB = Depends(deps.get_current_user)
):
    """
    Generate a LaTeX-formatted resume section using AI.
    """
    try:
        latex_code = await AIService.generate_section(request.section_name, request.user_context)
        return {"section_name": request.section_name, "latex_code": latex_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/score-resume")
async def score_resume(
    request: ScoreResumeRequest,
    current_user: UserInDB = Depends(deps.get_current_user)
):
    """
    Score a resume and get feedback using AI.
    """
    try:
        scoring_result = await AIService.score_resume(request.resume_text)
        return scoring_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
