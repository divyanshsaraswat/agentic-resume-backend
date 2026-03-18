from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from app.api import deps
from app.models.resume import ResumeInDB, ResumeCreate, ResumeVersion, ResumeStatus
from app.models.user import UserInDB, UserRole
from app.services.resume_service import ResumeService
from app.services.audit_service import AuditService
from app.models.audit_log import AuditActionType, AuditLogType

router = APIRouter()

@router.post("", response_model=ResumeInDB)
async def create_resume(
    type: str = Form(...),
    format: str = Form("latex"),
    initial_latex: Optional[str] = Form(""),
    file: Optional[UploadFile] = File(None),
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Create a new resume with optional file upload (PDF/DOCX).
    """
    resume_in = ResumeCreate(
        type=type,
        format=format,
        initial_latex=initial_latex
    )
    result = await ResumeService.create_resume(user_id=current_user.id, resume_in=resume_in, file=file)
    
    await AuditService.log_action(
        actor_id=str(current_user.id),
        actor_name=current_user.name,
        actor_role=current_user.role.value,
        action=AuditActionType.RESUME_CREATED,
        log_type=AuditLogType.RESUME,
        target=f"{type} resume ({format})",
    )
    
    return result

@router.get("", response_model=List[ResumeInDB])
async def read_resumes(
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Retrieve resumes for the current user.
    """
    return await ResumeService.get_student_resumes(user_id=current_user.id)

@router.get("/validation-queue", response_model=List[dict])
async def get_validation_queue(
    search: Optional[str] = None,
    year: Optional[List[int]] = Query(None),
    department: Optional[List[str]] = Query(None),
    group: Optional[str] = None,
    current_user: UserInDB = Depends(deps.check_role([UserRole.FACULTY, UserRole.ADMIN, UserRole.SPC]))
) -> Any:
    """
    Get the validation queue (Faculty/Admin/SPC only).
    """
    return await ResumeService.get_validation_queue(
        search=search,
        years=year,
        departments=department,
        department_group=group
    )

@router.get("/{resume_id}", response_model=ResumeInDB)
async def read_resume(
    resume_id: str,
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Get a specific resume by ID.
    """
    resume = await ResumeService.get_resume_by_id(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Check ownership or role
    if current_user.role == UserRole.STUDENT and resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return resume

@router.post("/{resume_id}/version", response_model=ResumeInDB)
async def add_version(
    resume_id: str,
    type: str = Form(...),
    format: str = Form("latex"),
    latex_code: str = Form(""),
    file: Optional[UploadFile] = File(None),
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Add a new version to a resume with optional file upload.
    """
    resume = await ResumeService.get_resume_by_id(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can add versions"
        )
    
    version_in = ResumeVersion(
        type=type,
        format=format,
        latex_code=latex_code
    )
    result = await ResumeService.add_resume_version(resume_id, version_in, file=file)
    
    await AuditService.log_action(
        actor_id=str(current_user.id),
        actor_name=current_user.name,
        actor_role=current_user.role.value,
        action=AuditActionType.VERSION_ADDED,
        log_type=AuditLogType.RESUME,
        target=f"v{len(resume.versions) + 1} ({type}, {format})",
    )
    
    return result

@router.patch("/{resume_id}/versions/{version_id}/status", response_model=bool)
async def update_status(
    resume_id: str,
    version_id: str,
    status: ResumeStatus,
    current_user: UserInDB = Depends(deps.check_role([UserRole.FACULTY, UserRole.ADMIN, UserRole.SPC]))
) -> Any:
    """
    Update resume version status (Faculty/Admin/SPC only).
    """
    success = await ResumeService.update_version_status(resume_id, version_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Resume version not found")
    
    audit_action = AuditActionType.RESUME_APPROVED if status == ResumeStatus.APPROVED else AuditActionType.RESUME_REJECTED
    await AuditService.log_action(
        actor_id=str(current_user.id),
        actor_name=current_user.name,
        actor_role=current_user.role.value,
        action=audit_action,
        log_type=AuditLogType.VALIDATION,
        target=f"Resume {resume_id} (version {version_id})",
    )
    
    return success

@router.patch("/{resume_id}", response_model=bool)
async def update_resume(
    resume_id: str,
    content_in: dict,
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Update the latest version of a resume.
    """
    resume = await ResumeService.get_resume_by_id(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can update the resume"
        )
    
    updates = content_in.copy()
    if "content" in updates:
        updates["latex_code"] = updates.pop("content")
        
    return await ResumeService.update_latest_version(resume_id, updates)

@router.delete("/{resume_id}", response_model=bool)
async def delete_resume(
    resume_id: str,
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Delete a resume.
    """
    success = await ResumeService.delete_resume(resume_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Resume not found or not owned by user")
    return success

@router.post("/{resume_id}/submit", response_model=bool)
async def submit_resume(
    resume_id: str,
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Submit the latest version of a resume for review.
    """
    resume = await ResumeService.get_resume_by_id(resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found or not owned by user")
    
    return await ResumeService.update_latest_version(resume_id, {"status": ResumeStatus.SUBMITTED})

@router.patch("/{resume_id}", response_model=bool)
async def update_resume(
    resume_id: str,
    content_in: dict,
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Update the latest version of a resume.
    """
    resume = await ResumeService.get_resume_by_id(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can update the resume"
        )
    
    updates = content_in.copy()
    if "content" in updates:
        updates["latex_code"] = updates.pop("content")
        
    return await ResumeService.update_latest_version(resume_id, updates)
@router.delete("/{resume_id}", response_model=bool)
async def delete_resume(
    resume_id: str,
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Delete a resume.
    """
    success = await ResumeService.delete_resume(resume_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Resume not found or not owned by user")
    return success

@router.post("/{resume_id}/submit", response_model=bool)
async def submit_resume(
    resume_id: str,
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Submit the latest version of a resume for review.
    """
    resume = await ResumeService.get_resume_by_id(resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found or not owned by user")
    
    return await ResumeService.update_latest_version(resume_id, {"status": ResumeStatus.SUBMITTED})
