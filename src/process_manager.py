"""
Process Manager for detecting, gracefully closing, and launching Riot Client processes.
"""

import subprocess
import time
from pathlib import Path
import psutil
from .config import Config


class ProcessManager:
    @staticmethod
    def get_running_riot_processes() -> list[psutil.Process]:
        """Return list of currently active Riot-related processes."""
        active = []
        target_names = {name.lower() for name in Config.RIOT_PROCESS_NAMES}
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = proc.info.get("name") or ""
                if name.lower() in target_names:
                    active.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return active

    @staticmethod
    def is_riot_running() -> bool:
        """Check if any Riot Client or game process is currently running."""
        return len(ProcessManager.get_running_riot_processes()) > 0

    @classmethod
    def close_all_riot_processes(cls, timeout: float = 4.0) -> bool:
        """
        Forcefully terminate all running Riot processes and their child process trees using taskkill.
        Waits until file locks are released.
        """
        target_exes = [
            "RiotClientServices.exe",
            "RiotClientUx.exe",
            "RiotClientUxRender.exe",
            "Riot Client.exe",
            "LeagueClient.exe",
            "LeagueClientUx.exe",
            "LeagueClientUxRender.exe",
            "VALORANT.exe",
            "VALORANT-Win64-Shipping.exe",
        ]

        for exe in target_exes:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/IM", exe],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
            except Exception:
                pass

        # Small grace period for Windows file locks to be released
        time.sleep(0.5)

        # Remove stale lockfile if it remains
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
        Runs detached so it continues running independently.
        """
        if not executable_path.is_file():
            raise FileNotFoundError(f"RiotClientServices.exe not found at: {executable_path}")

        prod_cfg = Config.PRODUCTS.get(product, Config.PRODUCTS["riot_client"])
        args = [str(executable_path)] + prod_cfg["args"]

        # Launch detached from current terminal/process
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

        subprocess.Popen(
            args,
            cwd=str(executable_path.parent),
            creationflags=flags,
            close_fds=True
        )
        return True
