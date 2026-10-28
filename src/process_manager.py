"""
Process Manager for detecting, gracefully closing, and launching Riot Client processes.
Uses Riot's official lockfile and native Windows system tools (zero process memory scanning).
"""

import subprocess
import time
from pathlib import Path
from typing import Optional, List
import psutil
from .config import Config


class ProcessManager:
    @staticmethod
    def get_riot_client_lockfile_pid() -> Optional[int]:
        """
        Read the active Riot Client PID directly from Riot's official lockfile.
        The lockfile format is: '<ProcessName>:<PID>:<Port>:<Password>:<Protocol>'
        Example: 'Riot Client:27836:60347:ayuKBM-eaptbv0gzNytVAA:https'
        Returns None if lockfile does not exist or cannot be parsed.
        """
        lockfile = Config.RIOT_CLIENT_CONFIG_DIR / "lockfile"
        if not lockfile.is_file():
            return None
        try:
            with open(lockfile, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
                parts = content.split(":")
                if len(parts) >= 2 and parts[1].isdigit():
                    return int(parts[1])
        except Exception:
            pass
        return None

    @classmethod
    def is_riot_running(cls) -> bool:
        """
        Passive check: returns True if Riot Client's official lockfile exists and is active.
        Zero system process enumeration, zero handle queries to game processes.
        """
        lockfile = Config.RIOT_CLIENT_CONFIG_DIR / "lockfile"
        if not lockfile.is_file():
            return False

        pid = cls.get_riot_client_lockfile_pid()
        if pid:
            try:
                # Check only this single specific PID
                if psutil.pid_exists(pid):
                    return True
                else:
                    # Stale lockfile left from an unexpected crash; clean it up
                    lockfile.unlink(missing_ok=True)
                    return False
            except Exception:
                return True
        return True

    @staticmethod
    def get_running_games() -> List[str]:
        """
        Check if any Riot game match (League of Legends, VALORANT) is currently running.
        Uses a single native Windows tasklist query (zero process handles opened from Python).
        """
        found = []
        CREATE_NO_WINDOW = 0x08000000

        try:
            res = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=2.0,
                check=False
            )
            output = (res.stdout or "").lower()
            for exe_name, display_name in Config.GAME_PROCESS_NAMES.items():
                if display_name not in found and exe_name.lower() in output:
                    found.append(display_name)
        except Exception:
            pass

        return found

    @classmethod
    def close_all_riot_processes(cls, timeout: float = 4.0) -> bool:
        """
        Closes all running Riot processes using targeted Windows taskkill (by client name and PID).
        Zero process scanning, zero memory hooks, 100% native Windows commands.
        """
        CREATE_NO_WINDOW = 0x08000000

        # 1. If active lockfile has the PID, kill that exact process tree directly
        lockfile_pid = cls.get_riot_client_lockfile_pid()
        if lockfile_pid:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(lockfile_pid)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW,
                    check=False
                )
            except Exception:
                pass

        # 2. Terminate Riot processes strictly by executable image name
        for name in Config.RIOT_PROCESS_NAMES:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/IM", name],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW,
                    check=False
                )
            except Exception:
                pass

        time.sleep(0.4)

        # 3. Clean up lockfile if it remains
        lockfile = Config.RIOT_CLIENT_CONFIG_DIR / "lockfile"
        if lockfile.exists():
            try:
                lockfile.unlink(missing_ok=True)
            except OSError:
                pass

        return not cls.is_riot_running()

    @classmethod
    def launch(cls, executable_path: Path, product: str = "riot_client") -> bool:
        """
        Launch Riot Client or a specific game (League of Legends, Valorant, TFT).
        Uses Windows ShellExecute (os.startfile) so it is launched by Windows Explorer
        directly, completely independent of Riot Link (identical to double-clicking
        an icon on your desktop).
        """
        if not executable_path.is_file():
            raise FileNotFoundError(f"RiotClientServices.exe not found at: {executable_path}")

        prod_cfg = Config.PRODUCTS.get(product, Config.PRODUCTS["riot_client"])
        args_list = prod_cfg.get("args", [])
        args_str = " ".join(args_list)

        import os
        try:
            # os.startfile triggers Win32 ShellExecuteW via Windows Explorer.
            # To Windows, this is identical to a user double-clicking a desktop shortcut.
            os.startfile(
                str(executable_path),
                operation="open",
                arguments=args_str,
                cwd=str(executable_path.parent)
            )
            return True
        except Exception:
            # Fallback to detached subprocess only if Windows ShellExecute fails
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_NO_WINDOW = 0x08000000
            flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW

            subprocess.Popen(
                [str(executable_path)] + args_list,
                cwd=str(executable_path.parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                close_fds=True
            )
            return True
