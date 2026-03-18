import logging
import subprocess
import os
import uuid
import shutil
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class LatexService:
    @staticmethod
    def _get_pdflatex_path() -> str:
        """
        Returns the path to pdflatex. On Windows, checks common MiKTeX installation 
        paths if it's not in the system PATH.
        """
        # 1. Try system PATH
        system_path = shutil.which("pdflatex")
        if system_path:
            logger.info(f"Using pdflatex from system PATH: {system_path}")
            return system_path
            
        # 2. Try common Windows MiKTeX paths
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
        return "pdflatex" # Fallback to default, which might fail if not in PATH

    @staticmethod
    async def compile_latex(latex_code: str) -> Dict[str, Any]:
        """
        Compiles LaTeX code to PDF.
        Returns a dictionary with success status, PDF path (ID), and logs.
        """
        job_id = str(uuid.uuid4())
        try:
            # Use the configured upload directory so it's served via /public
            work_dir = os.path.join(settings.UPLOAD_DIR, "temp_latex", job_id)
            os.makedirs(work_dir, exist_ok=True)
            
            logger.info(f"Starting LaTeX compilation job {job_id} in {work_dir}")
            logger.debug(f"LaTeX code length: {len(latex_code)} characters")
            
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
                tex_file
            ]
            
            logger.info(f"Executing command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=45 # Increased safety timeout
            )
            
            success = result.returncode == 0
            log_content = result.stdout
            err_content = result.stderr
            
            if not success:
                logger.error(f"LaTeX compilation failed with return code {result.returncode}")
                if err_content:
                    logger.error(f"Stderr: {err_content}")
            else:
                logger.info(f"LaTeX compilation successful for job {job_id}")
            
            # Extract error summary if failed
            error_msg = ""
            if not success:
                # Basic log parser for LaTeX errors
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
                "pdf_available": pdf_exists
            }
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"LaTeX compilation timed out: {e}")
            return {
                "success": False,
                "job_id": job_id,
                "error": "Compilation timed out",
                "log": (e.stdout.decode() if isinstance(e.stdout, bytes) else str(e.stdout)) if e.stdout else "No output available from timed-out process",
                "pdf_available": False
            }
        except FileNotFoundError:
            msg = "LaTeX build engine (pdflatex) not found. Please install MiKTeX (Windows) or TeX Live (Linux/macOS)."
            logger.error(msg)
            return {
                "success": False,
                "job_id": job_id,
                "error": msg,
                "log": "Fatal Error: 'pdflatex' executable was not found in the system path or common locations.",
                "pdf_available": False
            }
        except Exception as e:
            logger.error(f"Unexpected error during LaTeX compilation: {e}", exc_info=True)
            return {
                "success": False,
                "job_id": job_id,
                "error": str(e),
                "log": "",
                "pdf_available": False
            }
        finally:
            # Cleanup logic could be added here if needed
            pass

    @staticmethod
    def cleanup_job(job_id: str):
        work_dir = os.path.join(settings.UPLOAD_DIR, "temp_latex", job_id)
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
