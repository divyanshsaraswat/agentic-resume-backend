from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.api import deps
from app.models.resume import ResumeInDB, ResumeCreate, ResumeVersion, ResumeStatus
from app.models.user import UserInDB, UserRole
from app.services.resume_service import ResumeService

router = APIRouter()

@router.post("/", response_model=ResumeInDB)
async def create_resume(
    *,
    resume_in: ResumeCreate,
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Create a new resume.
    """
    return await ResumeService.create_resume(user_id=current_user.id, resume_in=resume_in)

@router.get("/", response_model=List[ResumeInDB])
async def read_resumes(
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Retrieve resumes for the current user.
    """
    return await ResumeService.get_student_resumes(user_id=current_user.id)

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
    version_in: ResumeVersion,
    current_user: UserInDB = Depends(deps.get_current_user)
) -> Any:
    """
    Add a new version to a resume.
    """
    resume = await ResumeService.get_resume_by_id(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can add versions"
        )
    
    return await ResumeService.add_resume_version(resume_id, version_in)

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
    return success
