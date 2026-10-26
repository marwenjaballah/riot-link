"""
Automatic updater for Riot Link using GitHub Releases.
Checks for new versions, downloads the executable, and performs seamless in-place restart.
"""

import os
import sys
import json
import time
import hashlib
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from .config import Config


def parse_version(ver_str: str) -> tuple:
    """Parse version string into tuple of integers for reliable comparison (e.g. 'v1.0.1' -> (1, 0, 1))."""
    cleaned = ver_str.strip().lstrip("v").strip()
    parts = []
    for p in cleaned.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


class UpdateManager:
    @staticmethod
    def check_for_updates(timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Query GitHub Releases API for the latest version.
        Returns release info dictionary if a newer version is available, else None.
        """
        try:
            req = urllib.request.Request(
                Config.GITHUB_API_LATEST_RELEASE,
                headers={
                    "User-Agent": f"RiotLink/{Config.APP_VERSION}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    return None
                data = json.loads(resp.read().decode("utf-8"))

            tag_name = data.get("tag_name", "")
            remote_ver = parse_version(tag_name)
            current_ver = parse_version(Config.APP_VERSION)

            if remote_ver > current_ver:
                # Find RiotLink.exe asset
                download_url = None
                asset_name = None
                asset_size = 0
                for asset in data.get("assets", []):
                    name = asset.get("name", "")
                    if name.lower() == "riotlink.exe":
                        download_url = asset.get("browser_download_url")
                        asset_name = name
                        asset_size = asset.get("size", 0)
                        break

                # Fallback to first .exe or release page
                if not download_url:
                    for asset in data.get("assets", []):
                        if asset.get("name", "").lower().endswith(".exe"):
                            download_url = asset.get("browser_download_url")
                            asset_name = asset.get("name")
                            asset_size = asset.get("size", 0)
                            break

                # Locate the published SHA256 checksums file
                checksums_url = None
                for asset in data.get("assets", []):
                    if asset.get("name", "").lower() == "checksums.txt":
                        checksums_url = asset.get("browser_download_url")
                        break

                return {
                    "tag": tag_name,
                    "version": tag_name.lstrip("v"),
                    "name": data.get("name") or tag_name,
                    "notes": data.get("body") or "New performance improvements and features.",
                    "download_url": download_url,
                    "asset_name": asset_name,
                    "checksums_url": checksums_url,
                    "html_url": data.get("html_url") or Config.GITHUB_RELEASES_URL,
                    "size": asset_size,
                }
        except Exception:
            pass
        return None

    @staticmethod
    def fetch_expected_sha256(checksums_url: str, asset_name: str, timeout: float = 15.0) -> str:
        """
        Download the release's checksums.txt and return the SHA256 for asset_name.
        Expected line format: '<HEX_SHA256>  RiotLink.exe'
        """
        req = urllib.request.Request(
            checksums_url,
            headers={"User-Agent": f"RiotLink/{Config.APP_VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8-sig", errors="ignore")

        for line in text.splitlines():
            parts = line.strip().split()
            if len(parts) == 2 and parts[1].lower() == asset_name.lower():
                digest = parts[0].lower()
                if len(digest) == 64 and all(c in "0123456789abcdef" for c in digest):
                    return digest
        raise RuntimeError(f"No SHA256 entry for '{asset_name}' found in checksums.txt.")

    @staticmethod
    def download_and_apply_update(
        download_url: str,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        checksums_url: Optional[str] = None,
        asset_name: Optional[str] = None,
    ) -> bool:
        """
        Download updated RiotLink.exe from GitHub, verify its SHA256 against the
        release's checksums.txt, and only then execute the in-place replacement.
        """
        if not checksums_url:
            raise RuntimeError(
                "This release has no checksums.txt, so the download can't be verified. "
                "Automatic update was cancelled for your safety."
            )
        asset_name = asset_name or "RiotLink.exe"

        # Determine the target executable path
        if getattr(sys, "frozen", False):
            target_exe = Path(sys.executable).resolve()
        else:
            # If running from source, target dist/RiotLink.exe
            target_exe = Config.APP_DATA_DIR.parent / "dist" / "RiotLink.exe"
            if not target_exe.parent.exists():
                target_exe = Path(__file__).resolve().parent.parent / "dist" / "RiotLink.exe"

        tmp_exe = target_exe.parent / f"{target_exe.stem}_new.tmp"
        updater_bat = target_exe.parent / "_apply_update.bat"

        try:
            expected_sha256 = UpdateManager.fetch_expected_sha256(checksums_url, asset_name)

            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": f"RiotLink/{Config.APP_VERSION}"}
            )

            hasher = hashlib.sha256()
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 64 * 1024  # 64 KB

                with open(tmp_exe, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        hasher.update(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            fraction = min(1.0, downloaded / total_size)
                            progress_callback(fraction, downloaded, total_size)

            actual_sha256 = hasher.hexdigest().lower()
            if actual_sha256 != expected_sha256:
                raise RuntimeError(
                    "Checksum mismatch — the downloaded file does not match the published SHA256.\n"
                    f"Expected: {expected_sha256}\nGot:      {actual_sha256}\n"
                    "The update was NOT installed."
                )

            # Generate updater batch script that guarantees old process termination, swaps .exe, and restarts
            current_pid = os.getpid()
            bat_script = f"""@echo off
chcp 65001 > nul
taskkill /F /PID {current_pid} > nul 2>&1
ping 127.0.0.1 -n 2 > nul
:retry
move /y "{tmp_exe}" "{target_exe}" > nul 2>&1
if errorlevel 1 (
    ping 127.0.0.1 -n 2 > nul
    goto retry
)
start "" "{target_exe}"
del "%~f0"
"""
            with open(updater_bat, "w", encoding="utf-8") as f:
                f.write(bat_script)

            # Launch updater batch detached
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_NO_WINDOW = 0x08000000
            flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW

            subprocess.Popen(
                ["cmd.exe", "/c", str(updater_bat)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                close_fds=True
            )
            return True
        except Exception as e:
            if tmp_exe.exists():
                try:
                    tmp_exe.unlink(missing_ok=True)
                except OSError:
                    pass
            raise RuntimeError(f"Update failed: {e}")
