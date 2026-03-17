import subprocess
import os
import uuid
import shutil
from typing import Dict, Any

class LatexService:
    @staticmethod
    async def compile_latex(latex_code: str) -> Dict[str, Any]:
        """
        Compiles LaTeX code to PDF.
        Returns a dictionary with success status, PDF path (ID), and logs.
        """
        job_id = str(uuid.uuid4())
        work_dir = os.path.join("/tmp", "latex", job_id)
        os.makedirs(work_dir, exist_ok=True)
        
        tex_file = os.path.join(work_dir, "resume.tex")
        pdf_file = os.path.join(work_dir, "resume.pdf")
        
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_code)
            
        try:
            # Run pdflatex
            # Flags:
            # -interaction=nonstopmode: Don't stop for errors
            # -halt-on-error: Stop at first error (optional, but good for speed)
            # -no-shell-escape: Security measure
            # -output-directory: Where to put files
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-no-shell-escape",
                    f"-output-directory={work_dir}",
                    tex_file
                ],
                capture_output=True,
                text=True,
                timeout=30 # Safety timeout
            )
            
            success = result.returncode == 0
            log_content = result.stdout
            
            # Extract error summary if failed
            error_msg = ""
            if not success:
                # Basic log parser for LaTeX errors
                for line in log_content.split("\n"):
                    if line.startswith("!"):
                        error_msg = line
                        break
            
            return {
                "success": success,
                "job_id": job_id,
                "error": error_msg,
                "log": log_content,
                "pdf_available": os.path.exists(pdf_file)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Compilation timed out",
                "log": "",
                "pdf_available": False
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "log": "",
                "pdf_available": False
            }
        finally:
            # We keep the directory for now so the PDF can be served/uploaded
            # In a real app, we'd clean up after upload to S3/R2
            pass

    @staticmethod
    def cleanup_job(job_id: str):
        work_dir = os.path.join("/tmp", "latex", job_id)
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
