"""
Riot Link — 1-Click Riot Account Switcher & Launcher
Entry point.
"""

import sys
from pathlib import Path

# Ensure src is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    import customtkinter as ctk
    import psutil
    import pydantic
    import yaml
except ImportError as e:
    print(f"Error: Missing required dependency: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

from src.single_instance import SingleInstanceManager
from src.gui.app import RiotAccountSwitcherApp


def cleanup_old_executable():
    """Clean up any .exe.old file left behind after an in-place self-update."""
    try:
        if getattr(sys, "frozen", False):
            exe_path = Path(sys.executable).resolve()
        else:
            exe_path = BASE_DIR / "dist" / "RiotLink.exe"
        old_exe = exe_path.with_suffix(".exe.old")
        if old_exe.is_file():
            old_exe.unlink(missing_ok=True)
    except Exception:
        pass


def main():
    cleanup_old_executable()

    # Ensure only a single instance runs at any time
    single_instance = SingleInstanceManager()
    if single_instance.is_already_running():
        # The running instance has been notified to focus and restore
        sys.exit(0)

    app = RiotAccountSwitcherApp(single_instance=single_instance)
    app.mainloop()


if __name__ == "__main__":
    main()
