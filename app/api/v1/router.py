from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, resumes, latex, ai

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(latex.router, prefix="/latex", tags=["latex"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])

@api_router.get("/health-check")
async def health_check():
    return {"status": "ok", "message": "API is running"}
