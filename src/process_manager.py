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
        Closes all running Riot processes cleanly:
        1. Sends a graceful close signal (WM_CLOSE) so Riot Client flushes settings (audio, video, preferences) to disk.
        2. Waits up to 2 seconds for a clean exit.
        3. Forcefully terminates any remaining stubborn processes if needed.
        4. Cleans up file locks.
        """
        if not cls.is_riot_running():
            return True

        target_exes = [
            "LeagueClientUx.exe",
            "LeagueClient.exe",
            "LeagueClientUxRender.exe",
            "VALORANT.exe",
            "VALORANT-Win64-Shipping.exe",
            "RiotClientUx.exe",
            "RiotClientUxRender.exe",
            "RiotClientServices.exe",
            "Riot Client.exe",
        ]

        # 1. Attempt graceful close without /F so settings are saved to disk
        for exe in target_exes:
            try:
                subprocess.run(
                    ["taskkill", "/IM", exe],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
            except Exception:
                pass

        # 2. Wait up to 1.8 seconds for processes to exit gracefully
        grace_start = time.time()
        while time.time() - grace_start < 1.8:
            if not cls.is_riot_running():
                break
            time.sleep(0.2)

        # 3. If any processes remain stubborn, force-kill them
        if cls.is_riot_running():
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
            time.sleep(0.4)

        # 4. Remove stale lockfile if it remains
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
