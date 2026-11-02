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
    def get_target_exe() -> Path:
        """Determine the target executable path."""
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve()
        target_exe = Config.APP_DATA_DIR.parent / "dist" / "RiotLink.exe"
        if not target_exe.parent.exists():
            target_exe = Path(__file__).resolve().parent.parent / "dist" / "RiotLink.exe"
        return target_exe

    @staticmethod
    def download_and_verify_update(
        download_url: str,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        checksums_url: Optional[str] = None,
        asset_name: Optional[str] = None,
    ) -> tuple[Path, Path]:
        """
        Download updated RiotLink.exe from GitHub and verify its SHA256 against checksums.txt.
        Returns (tmp_exe, target_exe) ready for in-place replacement.
        """
        if not checksums_url:
            raise RuntimeError(
                "This release has no checksums.txt, so the download can't be verified. "
                "Automatic update was cancelled for your safety."
            )
        asset_name = asset_name or "RiotLink.exe"
        target_exe = UpdateManager.get_target_exe()
        tmp_exe = target_exe.parent / f"{target_exe.stem}_new.tmp"

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

            return tmp_exe, target_exe
        except Exception as e:
            if tmp_exe.exists():
                try:
                    tmp_exe.unlink(missing_ok=True)
                except OSError:
                    pass
            raise RuntimeError(f"Update failed: {e}")

    @staticmethod
    def apply_update_and_restart(tmp_exe: Path, target_exe: Path):
        """
        Seamlessly apply the update without ANY command prompt (CMD) or console window.
        Spawns a completely hidden native wscript.exe helper (Windows GUI subsystem - strictly
        ZERO console allocation) that waits for this PID to exit, cleanly swaps the binary into
        place, launches the new version, and cleans up temporary files.
        """
        current_pid = os.getpid()
        old_exe = target_exe.with_suffix(".exe.old")
        vbs_path = target_exe.parent / "_silent_update.vbs"

        escaped_target = str(target_exe).replace('"', '""')
        escaped_old = str(old_exe).replace('"', '""')
        escaped_tmp = str(tmp_exe).replace('"', '""')

        vbs_code = f'''
Dim fso, wsh, wmi, procs
Set fso = CreateObject("Scripting.FileSystemObject")
Set wsh = CreateObject("WScript.Shell")

Dim targetPID, targetExe, oldExe, tmpExe
targetPID = {current_pid}
targetExe = "{escaped_target}"
oldExe = "{escaped_old}"
tmpExe = "{escaped_tmp}"

' 1. Wait for parent PID to exit completely
On Error Resume Next
Set wmi = GetObject("winmgmts:\\\\.\\root\\cimv2")
Do
    Set procs = wmi.ExecQuery("Select ProcessId from Win32_Process Where ProcessId = " & targetPID)
    If procs.Count = 0 Then Exit Do
    WScript.Sleep 150
Loop
On Error GoTo 0

' 2. Give the OS loader 250ms to release file locks
WScript.Sleep 250

' 3. Perform the swap
Dim i, success
success = False
For i = 1 To 30
    On Error Resume Next
    If fso.FileExists(targetExe) Then
        If fso.FileExists(oldExe) Then fso.DeleteFile oldExe, True
        fso.MoveFile targetExe, oldExe
    End If
    If fso.FileExists(tmpExe) Then
        fso.MoveFile tmpExe, targetExe
    End If
    On Error GoTo 0

    If fso.FileExists(targetExe) And Not fso.FileExists(tmpExe) Then
        success = True
        Exit For
    End If
    WScript.Sleep 200
Next

' 4. Clean up old binary
On Error Resume Next
If fso.FileExists(oldExe) Then fso.DeleteFile oldExe, True
On Error GoTo 0

' 5. Launch updated application (ZERO console window!)
If success Or fso.FileExists(targetExe) Then
    wsh.Run Chr(34) & targetExe & Chr(34), 1, False
End If

' 6. Self-delete this script
On Error Resume Next
fso.DeleteFile WScript.ScriptFullName, True
'''
        try:
            with open(vbs_path, "w", encoding="utf-8") as f:
                f.write(vbs_code.strip())

            wscript_exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "wscript.exe"
            wscript_cmd = str(wscript_exe) if wscript_exe.is_file() else "wscript.exe"

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

            subprocess.Popen(
                [wscript_cmd, "//B", "//NoLogo", str(vbs_path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=0x08000000,
                close_fds=True
            )
            os._exit(0)
        except Exception as e:
            raise RuntimeError(f"Could not apply update: {e}")

    @staticmethod
    def download_and_apply_update(
        download_url: str,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        checksums_url: Optional[str] = None,
        asset_name: Optional[str] = None,
    ) -> bool:
        """Convenience method to download, verify, apply, and restart in sequence."""
        tmp_exe, target_exe = UpdateManager.download_and_verify_update(
            download_url, progress_callback, checksums_url, asset_name
        )
        UpdateManager.apply_update_and_restart(tmp_exe, target_exe)
        return True
