# install_dependencies.py

import subprocess
import sys
import os

def install_dependencies():
    """
    Installs Python packages listed in requirements.txt using pip.
    Returns True if successful, False otherwise.
    """
    requirements_file = "requirement.txt" # Make sure this file is in the same directory

    if not os.path.exists(requirements_file):
        print(f"Error: '{requirements_file}' not found in the current directory.")
        print("Please ensure 'install_dependencies.py' and 'requirement.txt' are in the same folder.")
        return False # Indicate failure

    print(f"Attempting to install packages from {requirements_file}...")
    try:
        # Use subprocess to run pip install -r requirements.txt
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            check=True, # Raise CalledProcessError if the command returns a non-zero exit code
            capture_output=True, # Capture stdout and stderr
            text=True # Decode stdout and stderr as text
        )
        print("Packages installed successfully!")
        print("--- Pip Output ---")
        print(result.stdout)
        print("------------------")
        if result.stderr:
            print("--- Pip Errors/Warnings (if any) ---")
            print(result.stderr)
            print("------------------------------------")
        return True # Indicate success

    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to install packages. Command exited with code {e.returncode}")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        print("\nPlease ensure you have pip installed and an active internet connection.")
        return False # Indicate failure
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False # Indicate failure

def launch_vidra_downloader():
    """
    Launches the Vidra_downloader.py script.
    """
    downloader_script = "Vidra_downloader.py"
    if not os.path.exists(downloader_script):
        print(f"Error: '{downloader_script}' not found in the current directory.")
        print(f"Cannot launch '{downloader_script}'. Please ensure it's in the same folder.")
        return False
    
    print(f"\nLaunching '{downloader_script}'...")
    try:
        # Use Popen to run the downloader script, allowing this script to exit
        # if the user closes the terminal, but the downloader keeps running.
        # DETACHED_PROCESS is for Windows to fully detach, preexec_fn for Unix-like systems.
        if sys.platform == "win32":
            # For Windows, use DETACHED_PROCESS and no console window
            creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
            subprocess.Popen([sys.executable, downloader_script], creationflags=creationflags, close_fds=True)
        else:
            # For Unix-like systems, fork and detach
            subprocess.Popen([sys.executable, downloader_script], preexec_fn=os.setsid, close_fds=True)
        
        print(f"'{downloader_script}' launched successfully.")
        return True
    except Exception as e:
        print(f"Error launching '{downloader_script}': {e}")
        return False

if __name__ == "__main__":
    if install_dependencies():
        print("\nDependency installation complete.")
        launch_vidra_downloader()
    else:
        print("\nDependency installation failed. 'Vidra_downloader.py' will not be launched.")

