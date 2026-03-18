from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(message)s",
)
logger = logging.getLogger(__name__)

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from fastapi.staticfiles import StaticFiles
import os

# Ensure upload directory exists before any mounts
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup LaTeX if needed (non-blocking)
    try:
        from app.core.latex_setup import install_latex
        install_latex()
    except Exception as e:
        logger.error(f"Failed to run LaTeX setup: {e}")
        
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    redirect_slashes=False
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount static files
app.mount("/public", StaticFiles(directory=settings.UPLOAD_DIR), name="public")

@app.get("/")
async def root():
    return {"message": "Welcome to Placement ERP API"}
