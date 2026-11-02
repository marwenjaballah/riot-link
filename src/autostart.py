"""
Windows Autostart management for Riot Link via HKCU Registry.
"""

import sys
import winreg
from pathlib import Path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_KEY_NAME = "RiotLink"


def _get_launch_command(minimized: bool = True) -> str:
    """Build the command line string to launch Riot Link on startup without a console."""
    flag = " --minimized" if minimized else ""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return f'"{exe}"{flag}'
    else:
        main_py = Path(__file__).resolve().parent.parent / "main.py"
        py_exe = Path(sys.executable).resolve()
        # Prefer pythonw.exe (GUI subsystem) over python.exe so no CMD prompt appears
        pythonw = py_exe.with_name("pythonw.exe")
        if pythonw.is_file():
            py_exe = pythonw
        return f'"{py_exe}" "{main_py}"{flag}'


def is_autostart_enabled() -> bool:
    """Check if Riot Link is currently registered to start with Windows."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_KEY_NAME)
            return bool(val)
    except (FileNotFoundError, OSError):
        return False


def is_autostart_minimized() -> bool:
    """Check if the autostart entry is configured to start minimized."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_KEY_NAME)
            return "--minimized" in str(val)
    except (FileNotFoundError, OSError):
        return False


def set_autostart(enabled: bool, minimized: bool = True) -> bool:
    """Register or unregister Riot Link from starting on Windows boot."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                cmd = _get_launch_command(minimized=minimized)
                winreg.SetValueEx(key, APP_KEY_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_KEY_NAME)
                except FileNotFoundError:
                    pass
            return True
    except Exception:
        return False
