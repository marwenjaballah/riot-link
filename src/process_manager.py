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

    @staticmethod
    def get_running_games() -> list[str]:
        """
        Return display names of Riot games currently running (e.g. ["VALORANT"]).
        If non-empty, a match may be in progress and closing it could cause
        leaver penalties, so callers should ask the user before closing anything.
        """
        game_map = {k.lower(): v for k, v in Config.GAME_PROCESS_NAMES.items()}
        found = []
        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                label = game_map.get(name)
                if label and label not in found:
                    found.append(label)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return found

    @classmethod
    def close_all_riot_processes(cls, timeout: float = 4.0) -> bool:
        """
        Closes all running Riot processes cleanly using psutil (pure Win32, zero console popups):
        1. Gracefully calls proc.terminate() so Riot Client flushes settings to disk.
        2. Waits up to 1.8 seconds for a clean exit.
        3. Forcefully kills (proc.kill()) any remaining stubborn processes.
        4. Cleans up file locks.
        """
        procs = cls.get_running_riot_processes()
        if not procs:
            return True

        # Also collect child processes of each target process
        all_procs = []
        for p in procs:
            all_procs.append(p)
            try:
                all_procs.extend(p.children(recursive=True))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Deduplicate
        seen_pids = set()
        unique_procs = []
        for p in all_procs:
            if p.pid not in seen_pids:
                seen_pids.add(p.pid)
                unique_procs.append(p)

        # 1. Gracefully terminate
        for p in unique_procs:
            try:
                p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # 2. Wait up to 1.8 seconds for graceful exit
        gone, alive = psutil.wait_procs(unique_procs, timeout=1.8)

        # 3. Force-kill any stubborn remaining processes
        for p in alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Fallback to taskkill ONLY if something is still alive, strictly with CREATE_NO_WINDOW
        if cls.is_riot_running():
            CREATE_NO_WINDOW = 0x08000000
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

        time.sleep(0.3)

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
        Runs detached and without any console window.
        """
        if not executable_path.is_file():
            raise FileNotFoundError(f"RiotClientServices.exe not found at: {executable_path}")

        prod_cfg = Config.PRODUCTS.get(product, Config.PRODUCTS["riot_client"])
        args = [str(executable_path)] + prod_cfg["args"]

        # Launch detached and completely windowless from current process
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        CREATE_NO_WINDOW = 0x08000000
        flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW

        subprocess.Popen(
            args,
            cwd=str(executable_path.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            close_fds=True
        )
        return True
