#!/usr/bin/env python
import os
import sys
import subprocess

# --- Configuration ---
VENV_DIR = 'venv'
REQUIREMENTS_FILE = 'requirements.txt'

# --- Platform-specific setup ---
if os.name == 'nt':  # 'nt' is the name for Windows
    venv_python = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
    create_venv_cmd = f"python -m venv {VENV_DIR}"
else:  # 'posix' is the name for macOS/Linux
    venv_python = os.path.join(VENV_DIR, 'bin', 'python')
    create_venv_cmd = f"python3 -m venv {VENV_DIR}"

# --- Common Setup Function (MOVED UP) ---
def run_command(command_list, error_msg="Command failed"):
    """Runs a command and handles errors."""
    print(f"\nRunning: {' '.join(command_list)}")
    try:
        # Pass the current environment variables (including DJANGO_SETTINGS_MODULE)
        # to the subprocess.
        subprocess.run(command_list, check=True, env=os.environ)
    except subprocess.CalledProcessError as e:
        print(f"❌ {error_msg}: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Error: Command not found: '{command_list[0]}'.")
        if 'manage.py' in command_list:
            print("Make sure you are in the correct project root directory.")
        elif 'python' in command_list[0]:
             print("Make sure Python is installed and in your system's PATH.")
        sys.exit(1)

print("Starting MSP-ERP Django application locally...")

# --- Requirements File Check (MOVED UP) ---
# No point creating a venv if requirements are missing.
if not os.path.exists(REQUIREMENTS_FILE):
    print(f"❌ Error: '{REQUIREMENTS_FILE}' not found.")
    print("Cannot proceed without requirements file to install packages.")
    sys.exit(1)

# --- MODIFIED SECTION: Virtual Environment and Requirements Check ---
if not os.path.exists(venv_python):
    print(f"⚠️ Virtual environment not found. Creating one...")
    
    # 1. Create the venv
    venv_command_list = create_venv_cmd.split()
    run_command(venv_command_list, "Failed to create virtual environment")
    print(f"✅ Created virtual environment at: {VENV_DIR}")

    # 2. Install requirements (since it's a new venv)
    print(f"Installing requirements from {REQUIREMENTS_FILE}...")
    run_command(
        [venv_python, '-m', 'pip', 'install', '-r', REQUIREMENTS_FILE],
        "Failed to install requirements"
    )
    print("✅ Requirements installed")
    
else:
    # This is the new logic you requested:
    print(f"✅ Found existing virtual environment.")
    print("Skipping requirements installation.")

print(f"✅ Using Python from: {venv_python}")

# --- Main Execution ---
try:
    # Create logs directory
    os.makedirs("./logs", exist_ok=True)
    print("✅ Created logs directory")

    # Set Django settings environment variable
    os.environ['DJANGO_SETTINGS_MODULE'] = 'microsprings_inventory_system.settings'
    print("✅ Set DJANGO_SETTINGS_MODULE")

    # --- 'Install requirements' step REMOVED from here ---
    # (It's now handled in the venv check above)

    # Run database migrations
    print("Running database migrations...")
    run_command([venv_python, 'manage.py', 'makemigrations'], "Migrations check failed")
    run_command([venv_python, 'manage.py', 'migrate', '--noinput'], "Migration failed")

    # --- Start Server ---
    print("🚀 Starting Django development server...")
    print("Access the application at: http://localhost:8000")
    print("Admin panel at: http://localhost:8000/admin")
    print("\nPress Ctrl+C to stop the server")

    # This command runs until you stop it (Ctrl+C)
    run_command([venv_python, 'manage.py', 'runserver', '0.0.0.0:8000'], "Failed to start server")

except KeyboardInterrupt:
    print("\n\nStopping server...")
    sys.exit(0)