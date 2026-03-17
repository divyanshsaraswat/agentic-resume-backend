import platform
import subprocess
import sys
import os

def check_command(command):
    try:
        subprocess.run([command, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_latex():
    os_name = platform.system().lower()
    print(f"Detected OS: {platform.system()} {platform.release()}")
    
    if check_command("pdflatex"):
        print("✅ pdflatex is already installed.")
        return

    print("pdflatex not found. Preparing installation instructions...")

    if os_name == "linux":
        distro = platform.freedesktop_os_release().get("ID", "").lower()
        if "ubuntu" in distro or "debian" in distro:
            print("\nSuggested command for Ubuntu/Debian:")
            print("sudo apt update && sudo apt install -y texlive-latex-base texlive-latex-extra texlive-fonts-recommended texlive-latex-recommended texlive-xetex")
        else:
            print("\nPlease install TeX Live using your distribution's package manager.")
            
    elif os_name == "darwin": # macOS
        print("\nSuggested command for macOS (using Homebrew):")
        print("brew install --cask mactex")
        print("Alternatively, download Basic-TeX: https://www.tug.org/mactex/morepackages.html")
        
    elif os_name == "windows":
        print("\nSuggested installation for Windows:")
        print("1. Download MiKTeX: https://miktex.org/download")
        print("2. OR Install TeX Live: https://www.tug.org/texlive/windows.html")
        print("3. Ensure the bin directory is added to your PATH.")
    
    else:
        print(f"\nUnsupported OS: {os_name}. Please install LaTeX manually.")

if __name__ == "__main__":
    install_latex()
