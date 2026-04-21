import sys
import ctypes
import subprocess

def main():
    # Bootstrap dependencies before core imports
    from src.config import REQUIRED_MODULES
    for module in REQUIRED_MODULES:
        try:
            name = "PIL" if module == "Pillow" else module
            __import__(name)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", module])

    # Now safe to launch core app
    from src.ui.app import VidraApp

    # Windows DPI awareness for crispy UI
    if sys.platform == "win32":
        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except: pass

    app = VidraApp()
    app.mainloop()

if __name__ == "__main__":
    main()