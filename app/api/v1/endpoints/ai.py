from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from app.api import deps
from app.models.user import UserInDB
from app.services.ai_service import AIService
from app.services.audit_service import AuditService
from app.models.audit_log import AuditActionType, AuditLogType

router = APIRouter()

class ImproveBulletRequest(BaseModel):
    bullet: str

class GenerateSectionRequest(BaseModel):
    section_name: str
    user_context: str

class ScoreResumeRequest(BaseModel):
    resume_text: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

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
        await AuditService.log_action(
            actor_id=str(current_user.id),
            actor_name=current_user.name,
            actor_role=current_user.role.value,
            action=AuditActionType.AI_IMPROVE_BULLET,
            log_type=AuditLogType.AI,
            target="Resume Bullet",
        )
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
        await AuditService.log_action(
            actor_id=str(current_user.id),
            actor_name=current_user.name,
            actor_role=current_user.role.value,
            action=AuditActionType.AI_GENERATE_SECTION,
            log_type=AuditLogType.AI,
            target=request.section_name,
        )
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
        await AuditService.log_action(
            actor_id=str(current_user.id),
            actor_name=current_user.name,
            actor_role=current_user.role.value,
            action=AuditActionType.AI_SCORE_RESUME,
            log_type=AuditLogType.AI,
            target="Resume Content",
            metadata={"score": scoring_result.get("score")}
        )
        return scoring_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    current_user: UserInDB = Depends(deps.get_current_user)
):
    """
    Stream AI chat responses.
    """
    async def event_generator():
        try:
            # Convert pydantic models to dicts and map 'ai' to 'assistant'
            messages = []
            for m in request.messages:
                role = "assistant" if m.role == "ai" else m.role
                messages.append({"role": role, "content": m.content})
            
            await AuditService.log_action(
                actor_id=str(current_user.id),
                actor_name=current_user.name,
                actor_role=current_user.role.value,
                action=AuditActionType.AI_CHAT,
                log_type=AuditLogType.AI,
                target="AI Assistant",
                metadata={"message_count": len(request.messages)}
            )
            async for chunk in AIService.stream_chat(messages):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"}
    )
