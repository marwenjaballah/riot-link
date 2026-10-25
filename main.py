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

from src.gui.app import RiotAccountSwitcherApp


def main():
    app = RiotAccountSwitcherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
