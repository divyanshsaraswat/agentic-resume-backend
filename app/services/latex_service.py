import asyncio
import logging
import os
import uuid
import shutil
import time
from typing import Dict, Any, Optional
from fastapi import WebSocket
from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Job Queue System — max 2 concurrent LaTeX compilations
# ---------------------------------------------------------------------------
_job_queue: Optional[asyncio.Queue] = None
_workers_started = False
_job_store: Dict[str, Dict[str, Any]] = {}  # job_id -> {status, result, event}

AVG_COMPILE_SECONDS = 5  # estimated average compile time for ETA


class ConnectionManager:
    """Manages WebSocket connections keyed by job_id."""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        self.connections[job_id] = websocket

    def disconnect(self, job_id: str):
        self.connections.pop(job_id, None)

    async def send(self, job_id: str, message: dict):
        ws = self.connections.get(job_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(job_id)

    async def broadcast_queue_positions(self):
        """Notify all queued jobs of their updated position."""
        if _job_queue is None:
            return
        queued_jobs = [
            jid for jid, info in _job_store.items()
            if info.get("status") == "queued"
        ]
        for i, jid in enumerate(queued_jobs):
            await self.send(jid, {
                "status": "queued",
                "position": i + 1,
                "queue_length": len(queued_jobs),
                "eta_seconds": (i + 1) * AVG_COMPILE_SECONDS,
            })


ws_manager = ConnectionManager()


def _ensure_queue():
    """Lazily create the queue (must be called inside a running event loop)."""
    global _job_queue
    if _job_queue is None:
        _job_queue = asyncio.Queue()


async def _start_workers():
    """Start 2 background workers if not already running."""
    global _workers_started
    if _workers_started:
        return
    _workers_started = True
    _ensure_queue()
    for i in range(2):
        asyncio.create_task(_latex_worker(i))
        logger.info(f"LaTeX worker {i} started")


async def _latex_worker(worker_id: int):
    """Continuously pulls jobs from the queue and compiles them."""
    while True:
        job = await _job_queue.get()  # type: ignore[union-attr]
        job_id = job["id"]
        latex_code = job["content"]

        logger.info(f"Worker {worker_id} picked up job {job_id}")

        # Notify: processing
        _job_store[job_id]["status"] = "processing"
        await ws_manager.send(job_id, {
            "status": "processing",
            "message": "Compilation started",
        })
        # Update positions for remaining queued jobs
        await ws_manager.broadcast_queue_positions()

        # Run compilation
        result = await LatexService._run_compilation(job_id, latex_code)

        # Store result and signal completion
        _job_store[job_id]["result"] = result
        _job_store[job_id]["status"] = "completed" if result["success"] else "error"

        # Notify via WebSocket
        if result["success"]:
            pdf_url = f"/public/temp_latex/{job_id}/resume.pdf" if result.get("pdf_available") else None
            await ws_manager.send(job_id, {
                "status": "completed",
                "pdf_url": pdf_url,
                "job_id": job_id,
            })
        else:
            await ws_manager.send(job_id, {
                "status": "error",
                "error": result.get("error", "Unknown error"),
                "log": result.get("log", ""),
            })

        # Signal waiter (for sync compile_latex path)
        event = _job_store[job_id].get("event")
        if event:
            event.set()

        _job_queue.task_done()  # type: ignore[union-attr]


class LatexService:
    @staticmethod
    def _get_pdflatex_path() -> str:
        """
        Returns the path to pdflatex. On Windows, checks common MiKTeX installation
        paths if it's not in the system PATH.
        """
        system_path = shutil.which("pdflatex")
        if system_path:
            logger.info(f"Using pdflatex from system PATH: {system_path}")
            return system_path

        if os.name == "nt":
            user_home = os.path.expanduser("~")
            paths = [
                os.path.join(user_home, "AppData", "Local", "Programs", "MiKTeX", "miktex", "bin", "x64", "pdflatex.exe"),
                os.path.join("C:\\", "Program Files", "MiKTeX", "miktex", "bin", "x64", "pdflatex.exe"),
            ]
            for path in paths:
                if os.path.exists(path):
                    logger.info(f"Using pdflatex from MiKTeX path: {path}")
                    return path

        logger.warning("pdflatex not found in PATH or standard locations. Falling back to 'pdflatex' command.")
        return "pdflatex"

    # ------------------------------------------------------------------
    # Async (fire-and-forget) submission — used by new WebSocket flow
    # ------------------------------------------------------------------
    @staticmethod
    async def submit_job(latex_code: str) -> Dict[str, Any]:
        """
        Submit a LaTeX compilation job to the queue.
        Returns immediately with job_id and queue position.
        """
        if len(latex_code) > 100_000:
            return {"error": "LaTeX source too large (max 100KB)"}

        await _start_workers()

        job_id = str(uuid.uuid4())
        event = asyncio.Event()

        _job_store[job_id] = {
            "status": "queued",
            "result": None,
            "event": event,
            "created_at": time.time(),
        }

        await _job_queue.put({"id": job_id, "content": latex_code})  # type: ignore[union-attr]

        # Calculate position
        queued_count = sum(1 for info in _job_store.values() if info.get("status") == "queued")

        # Broadcast updated positions to all waiting jobs
        await ws_manager.broadcast_queue_positions()

        return {
            "job_id": job_id,
            "queue_position": queued_count,
            "eta_seconds": queued_count * AVG_COMPILE_SECONDS,
        }

    # ------------------------------------------------------------------
    # Synchronous wrapper — used by existing /latex/compile endpoint
    # ------------------------------------------------------------------
    @staticmethod
    async def compile_latex(latex_code: str) -> Dict[str, Any]:
        """
        Synchronous compile: submits to queue, waits for result, returns it.
        Backward-compatible with the existing /latex/compile endpoint.
        """
        submission = await LatexService.submit_job(latex_code)
        if "error" in submission:
            return {
                "success": False,
                "job_id": "",
                "error": submission["error"],
                "log": "",
                "pdf_available": False,
            }

        job_id = submission["job_id"]
        event = _job_store[job_id]["event"]

        # Wait for the worker to finish (timeout = 60s)
        try:
            await asyncio.wait_for(event.wait(), timeout=60)
        except asyncio.TimeoutError:
            _job_store.pop(job_id, None)
            return {
                "success": False,
                "job_id": job_id,
                "error": "Compilation timed out in queue",
                "log": "",
                "pdf_available": False,
            }

        result = _job_store[job_id].get("result", {})
        # Clean up store after retrieval (sync path doesn't need it anymore)
        _job_store.pop(job_id, None)

        return result

    # ------------------------------------------------------------------
    # Get job status (polling fallback)
    # ------------------------------------------------------------------
    @staticmethod
    def get_job_status(job_id: str) -> Dict[str, Any]:
        """Returns current status of a job."""
        info = _job_store.get(job_id)
        if not info:
            return {"status": "not_found"}

        response: Dict[str, Any] = {"status": info["status"]}

        if info["status"] == "queued":
            queued_jobs = [jid for jid, i in _job_store.items() if i.get("status") == "queued"]
            try:
                pos = queued_jobs.index(job_id) + 1
            except ValueError:
                pos = 0
            response["position"] = pos
            response["eta_seconds"] = pos * AVG_COMPILE_SECONDS

        if info["status"] in ("completed", "error") and info.get("result"):
            result = info["result"]
            response["success"] = result.get("success", False)
            response["error"] = result.get("error", "")
            if result.get("pdf_available"):
                response["pdf_url"] = f"/public/temp_latex/{job_id}/resume.pdf"

        return response

    # ------------------------------------------------------------------
    # Internal compilation (unchanged logic)
    # ------------------------------------------------------------------
    @staticmethod
    async def _run_compilation(job_id: str, latex_code: str) -> Dict[str, Any]:
        """Runs pdflatex in a thread pool (works on all platforms including Windows)."""
        try:
            work_dir = os.path.join(settings.UPLOAD_DIR, "temp_latex", job_id)
            os.makedirs(work_dir, exist_ok=True)

            logger.info(f"Starting LaTeX compilation job {job_id} in {work_dir}")

            tex_file = os.path.join(work_dir, "resume.tex")
            pdf_file = os.path.join(work_dir, "resume.pdf")

            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_code)

            pdflatex_cmd = LatexService._get_pdflatex_path()

            cmd = [
                pdflatex_cmd,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-no-shell-escape",
                f"-output-directory={work_dir}",
                tex_file,
            ]

            logger.info(f"Executing command: {' '.join(cmd)}")

            # Run subprocess in thread pool so it doesn't block the event loop.
            # asyncio.create_subprocess_exec raises NotImplementedError on Windows.
            import subprocess
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=45,
                )
            except subprocess.TimeoutExpired as e:
                logger.error(f"LaTeX compilation timed out for job {job_id}")
                return {
                    "success": False,
                    "job_id": job_id,
                    "error": "Compilation timed out",
                    "log": (e.stdout or "Process killed after 45 second timeout"),
                    "pdf_available": False,
                }

            log_content = result.stdout or ""
            err_content = result.stderr or ""
            success = result.returncode == 0

            if not success:
                logger.error(f"LaTeX compilation failed with return code {result.returncode}")
                if err_content:
                    logger.error(f"Stderr: {err_content}")
            else:
                logger.info(f"LaTeX compilation successful for job {job_id}")

            error_msg = ""
            if not success:
                for line in log_content.split("\n"):
                    if line.startswith("!"):
                        error_msg = line
                        break
                if not error_msg and err_content:
                    error_msg = err_content.split("\n")[0]

            pdf_exists = os.path.exists(pdf_file)
            if success and not pdf_exists:
                logger.error(f"pdflatex claimed success but {pdf_file} was not found")

            return {
                "success": success,
                "job_id": job_id,
                "error": error_msg or ("Unknown error" if not success else ""),
                "log": log_content,
                "pdf_available": pdf_exists,
            }

        except FileNotFoundError:
            msg = "LaTeX build engine (pdflatex) not found. Please install MiKTeX (Windows) or TeX Live (Linux/macOS)."
            logger.error(msg)
            return {
                "success": False,
                "job_id": job_id,
                "error": msg,
                "log": "Fatal Error: 'pdflatex' executable was not found in the system path or common locations.",
                "pdf_available": False,
            }
        except Exception as e:
            logger.error(f"Unexpected error during LaTeX compilation: {e}", exc_info=True)
            return {
                "success": False,
                "job_id": job_id,
                "error": str(e),
                "log": "",
                "pdf_available": False,
            }

    @staticmethod
    def cleanup_job(job_id: str):
        work_dir = os.path.join(settings.UPLOAD_DIR, "temp_latex", job_id)
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        _job_store.pop(job_id, None)

    @staticmethod
    def get_queue_info() -> Dict[str, int]:
        """Returns current queue status for monitoring."""
        return {
            "waiting": sum(1 for info in _job_store.values() if info.get("status") == "queued"),
            "processing": sum(1 for info in _job_store.values() if info.get("status") == "processing"),
            "max_concurrent": 2,
        }
