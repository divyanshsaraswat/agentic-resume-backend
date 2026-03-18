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

    print("pdflatex not found. Attempting automatic setup...")

    if os_name == "linux":
        try:
            # Check for apt (Debian/Ubuntu)
            if check_command("apt-get"):
                print("Detected Debian/Ubuntu. Installing TeX Live...")
                # Try to install without sudo first (in case we're root)
                cmd = ["apt-get", "update"]
                subprocess.run(cmd, capture_output=True)
                
                cmd = ["apt-get", "install", "-y", 
                       "texlive-latex-base", 
                       "texlive-latex-recommended", 
                       "texlive-latex-extra", 
                       "texlive-fonts-recommended", 
                       "texlive-fonts-extra",
                       "texlive-science",
                       "texlive-xetex",
                       "texlive-luatex"]
                # If not root, prepend sudo
                if os.geteuid() != 0:
                    cmd = ["sudo"] + cmd
                
                print(f"Running: {' '.join(cmd)}")
                subprocess.run(cmd, check=True)
                print("✅ LaTeX installed successfully.")
            else:
                print("❌ Automatic installation only supported on Debian/Ubuntu via apt-get.")
        except Exception as e:
            print(f"❌ Failed to install LaTeX: {e}")
            
    elif os_name == "darwin": # macOS
        print("\nSuggested command for macOS (using Homebrew):")
        print("brew install --cask mactex")
        
    elif os_name == "windows":
        print("\nSuggested installation for Windows: Install MiKTeX (https://miktex.org/download)")
    
    else:
        print(f"\nUnsupported OS: {os_name}.")

if __name__ == "__main__":
    install_latex()
