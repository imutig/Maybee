#!/usr/bin/env python3
"""
MaybeBot Enhanced Setup Script
Automates the installation and configuration process
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_step(step_num, total_steps, message):
    """Print a formatted step message"""
    print(f"\n[{step_num}/{total_steps}] {message}")
    print("-" * 50)

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True

def install_dependencies():
    """Install required Python packages"""
    try:
        print("Installing Python dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_environment():
    """Setup environment configuration"""
    env_file = Path(".env")
    template_file = Path(".env.template")
    
    if env_file.exists():
        print("⚠️  .env file already exists")
        response = input("Do you want to overwrite it? (y/N): ").lower()
        if response != 'y':
            print("Skipping environment setup")
            return True
    
    if template_file.exists():
        shutil.copy(template_file, env_file)
        print("✅ .env file created from template")
        print("🔧 Please edit .env file with your configuration before running the bot")
        return True
    else:
        print("❌ .env.template not found")
        return False

def check_database():
    """Check database requirements"""
    print("📋 Database Setup Checklist:")
    print("1. MySQL 5.7+ installed and running")
    print("2. Database created (e.g., 'maybebot')")
    print("3. User with proper permissions")
    print("4. Import database_schema.sql")
    print("\nExample commands:")
    print("mysql -u root -p -e 'CREATE DATABASE maybebot;'")
    print("mysql -u root -p maybebot < database_schema.sql")
    
    response = input("\nHave you completed the database setup? (y/N): ").lower()
    return response == 'y'

def create_directories():
    """Create necessary directories"""
    directories = [
        "cache_data",
        "logs",
        "__pycache__"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Required directories created")

def run_migration():
    """Ask user if they want to run migration"""
    migration_file = Path("migrate_yaml_to_db.py")
    
    if migration_file.exists():
        response = input("Do you want to run the database migration script? (y/N): ").lower()
        if response == 'y':
            try:
                subprocess.check_call([sys.executable, "migrate_yaml_to_db.py"])
                print("✅ Migration completed successfully")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Migration failed: {e}")
                return False
    else:
        print("ℹ️  No migration script found")
    
    return True

def main():
    """Main setup function"""
    print("🚀 MaybeBot Enhanced Setup Script")
    print("=" * 50)
    
    steps = [
        ("Checking Python version", check_python_version),
        ("Installing dependencies", install_dependencies),
        ("Setting up environment", setup_environment),
        ("Creating directories", lambda: (create_directories(), True)[1]),
        ("Checking database setup", check_database),
        ("Running migration (optional)", run_migration)
    ]
    
    for i, (description, func) in enumerate(steps, 1):
        print_step(i, len(steps), description)
        
        if not func():
            print(f"\n❌ Setup failed at step {i}: {description}")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Edit .env file with your Discord token and database credentials")
    print("2. Ensure your MySQL database is set up and accessible")
    print("3. Run the bot with: python main.py")
    print("\n🔗 For support, check the README.md or create an issue on GitHub")

if __name__ == "__main__":
    main()
