import platform
import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def check_command(command):
    try:
        subprocess.run([command, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_latex():
    os_name = platform.system().lower()
    
    if check_command("pdflatex"):
        return

    logger.info("pdflatex not found. Attempting automatic setup...")

    if os_name == "linux":
        try:
            if check_command("apt-get"):
                logger.info("Detected Debian/Ubuntu. Installing TeX Live package collection...")
                
                # Check if we have root privileges (Linux specific)
                is_root = False
                if hasattr(os, 'geteuid'):
                    is_root = os.geteuid() == 0
                
                # Update package list
                subprocess.run(["apt-get", "update"], capture_output=True)
                
                cmd = ["apt-get", "install", "-y", 
                       "texlive-latex-base", 
                       "texlive-latex-recommended", 
                       "texlive-latex-extra", 
                       "texlive-fonts-recommended", 
                       "texlive-fonts-extra",
                       "texlive-science",
                       "texlive-xetex",
                       "texlive-luatex"]
                
                if not is_root:
                    cmd = ["sudo"] + cmd
                
                subprocess.run(cmd, check=True)
                logger.info("✅ LaTeX installed successfully.")
            else:
                logger.warning("❌ Automatic installation only supported on Debian/Ubuntu via apt-get.")
        except Exception as e:
            logger.error(f"❌ Failed to install LaTeX: {e}")
            
    elif os_name == "darwin":
        logger.info("Suggested command for macOS: brew install --cask mactex")
        
    elif os_name == "windows":
        logger.info("Suggested setup for Windows: Install MiKTeX (https://miktex.org/download)")
