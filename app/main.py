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

# Ensure upload directory exists before any mounts or StaticFiles init
# This must happen at the top level for StaticFiles to satisfy its existence check
try:
    if not os.path.exists(settings.UPLOAD_DIR):
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
except OSError:
    import tempfile
    fallback_dir = os.path.join(tempfile.gettempdir(), "resume_app")
    os.makedirs(fallback_dir, exist_ok=True)
    settings.UPLOAD_DIR = fallback_dir
    logger.warning(f"Using fallback temporary storage: {settings.UPLOAD_DIR}")

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

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    redirect_slashes=False
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"VALIDATION ERROR: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)},
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

# WebSocket endpoint for live LaTeX compilation updates
from fastapi import WebSocket as _WS, WebSocketDisconnect as _WSD
from app.services.latex_service import ws_manager

@app.websocket("/ws/latex/{job_id}")
async def latex_ws(websocket: _WS, job_id: str):
    await ws_manager.connect(websocket, job_id)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except _WSD:
        ws_manager.disconnect(job_id)
    except Exception:
        ws_manager.disconnect(job_id)

# Mount static files
app.mount("/public", StaticFiles(directory=settings.UPLOAD_DIR), name="public")

@app.get("/")
async def root():
    return {"message": "Welcome to Placement ERP API"}
