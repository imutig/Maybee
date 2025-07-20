"""
Web Dashboard Launcher for Maybee
Simple script to launch the web dashboard
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🚀 Maybee Web Dashboard Launcher")
    print("=" * 40)
    
    # Change to web directory
    web_dir = Path(__file__).parent
    os.chdir(web_dir)
    
    # Check if virtual environment should be used
    venv_python = None
    if os.path.exists("venv"):
        if os.name == 'nt':  # Windows
            venv_python = "venv\\Scripts\\python.exe"
        else:  # Unix/Linux/Mac
            venv_python = "venv/bin/python"
    
    python_cmd = venv_python if venv_python and os.path.exists(venv_python) else "python"
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        print("⚠️  Warning: .env file not found!")
        print("📄 Please copy .env.example to .env and configure your settings.")
        print("")
        
        create_env = input("Create .env file from template? (y/n): ").lower().strip()
        if create_env == 'y':
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file. Please edit it with your configuration.")
            return
        else:
            print("❌ Cannot start without .env configuration.")
            return
    
    print("🔧 Checking dependencies...")
    
    # Install requirements if needed
    try:
        subprocess.run([python_cmd, "-c", "import fastapi"], check=True, capture_output=True)
        print("✅ Dependencies already installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("📦 Installing web dependencies...")
        try:
            subprocess.run([python_cmd, "-m", "pip", "install", "-r", "../web_requirements.txt"], check=True)
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return
        except FileNotFoundError:
            print("❌ Python not found. Please ensure Python is installed and in PATH.")
            return
    
    print("🌐 Starting web dashboard...")
    print("📍 Dashboard will be available at: http://localhost:8000")
    print("🔑 Make sure to configure Discord OAuth2 in your Discord application:")
    print("   - Redirect URI: http://localhost:8000/auth/discord/callback")
    print("")
    print("Press Ctrl+C to stop the dashboard")
    print("=" * 40)
    
    try:
        # Start the web server
        subprocess.run([python_cmd, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except FileNotFoundError:
        print("❌ Failed to start dashboard. Please check your Python installation.")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    main()
