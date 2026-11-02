"""
Process Manager for detecting, gracefully closing, and launching Riot Client processes.
Uses Riot's official lockfile and native Windows system tools (zero process memory scanning).
NEVER interacts with or forcefully terminates live game processes (VALORANT, League of Legends).
"""

import subprocess
import time
import os
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
        Verifies the PID actually belongs to Riot Client launcher (not a recycled OS PID).
        Zero memory hooks, zero handle queries to protected game processes.
        """
        lockfile = Config.RIOT_CLIENT_CONFIG_DIR / "lockfile"
        if not lockfile.is_file():
            return False

        pid = cls.get_riot_client_lockfile_pid()
        if pid:
            try:
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    proc_name = proc.name().lower()
                    if any(proc_name == r.lower() for r in Config.RIOT_CLIENT_PROCESSES):
                        return True
                    else:
                        # Stale lockfile whose PID was recycled by another program; clean up
                        lockfile.unlink(missing_ok=True)
                        return False
                else:
                    # Stale lockfile from previous crash; clean up
                    lockfile.unlink(missing_ok=True)
                    return False
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False
            except Exception:
                return False
        return False

    @staticmethod
    def get_running_games() -> List[str]:
        """
        Check if any Riot game match (League of Legends, VALORANT) is currently running.
        Uses pure-Python psutil process snapshot (zero console executables spawned).
        """
        found = []
        target_map = {exe.lower(): display for exe, display in Config.GAME_PROCESS_NAMES.items()}
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    pname = proc.info.get('name')
                    if pname and pname.lower() in target_map:
                        disp = target_map[pname.lower()]
                        if disp not in found:
                            found.append(disp)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass

        return found

    @classmethod
    def close_all_riot_processes(cls, timeout: float = 4.0) -> bool:
        """Alias for close_riot_client_launcher."""
        return cls.close_riot_client_launcher(timeout=timeout)

    @classmethod
    def close_riot_client_launcher(cls, timeout: float = 4.0) -> bool:
        """
        Closes ONLY the Riot Client launcher UI processes (RiotClientServices.exe, RiotClientUx.exe).
        NEVER terminates game processes (League of Legends, VALORANT).
        Uses pure-Python psutil termination (zero console executables spawned).
        """
        launcher_names = {p.lower() for p in Config.RIOT_CLIENT_PROCESSES}
        procs_to_terminate = []

        # 1. Target lockfile PID if it belongs to Riot Client launcher
        lockfile_pid = cls.get_riot_client_lockfile_pid()
        if lockfile_pid and psutil.pid_exists(lockfile_pid):
            try:
                proc = psutil.Process(lockfile_pid)
                if proc.name().lower() in launcher_names:
                    procs_to_terminate.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # 2. Find any other running Riot Client launcher processes
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    pname = proc.info.get('name')
                    if pname and pname.lower() in launcher_names:
                        if proc not in procs_to_terminate:
                            procs_to_terminate.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass

        # Terminate gracefully first
        for proc in procs_to_terminate:
            try:
                proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        gone, alive = psutil.wait_procs(procs_to_terminate, timeout=min(2.0, timeout))
        for proc in alive:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        time.sleep(0.2)

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
        Launch the official Riot Client cleanly.
        Uses Windows ShellExecute (os.startfile) so it is launched by Windows Explorer
        directly, completely independent of Riot Link (identical to double-clicking
        the official Riot Client icon on your desktop).
        Zero command-line game tampering.
        """
        if not executable_path.is_file():
            raise FileNotFoundError(f"RiotClientServices.exe not found at: {executable_path}")

        try:
            # os.startfile triggers Win32 ShellExecuteW via Windows Explorer.
            # To Windows and Vanguard, this is identical to a user double-clicking a desktop shortcut.
            os.startfile(
                str(executable_path),
                operation="open",
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
                [str(executable_path)],
                cwd=str(executable_path.parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                close_fds=True
            )
            return True
