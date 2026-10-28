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


def main():
    # Ensure only a single instance runs at any time
    single_instance = SingleInstanceManager()
    if single_instance.is_already_running():
        # The running instance has been notified to focus and restore
        sys.exit(0)

    app = RiotAccountSwitcherApp(single_instance=single_instance)
    app.mainloop()


if __name__ == "__main__":
    main()
