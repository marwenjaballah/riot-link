"""
Session Manager for backing up, restoring, and switching Riot Client account sessions.
"""

import os
import json
import shutil
import hashlib
import zipfile
from pathlib import Path
from typing import List, Optional
import yaml

from .config import Config
from .models import AccountProfile, AppSettings
from .process_manager import ProcessManager
from .autostart import is_autostart_enabled, set_autostart
from .logger import get_logger

logger = get_logger("SessionManager")


def _write_json_atomic(filepath: Path, data: dict):
    """Write dictionary to file atomically via a temporary file to prevent corruption."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = filepath.parent / f"{filepath.name}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_file, filepath)


class SessionManager:
    def __init__(self):
        Config.ensure_directories()
        self.settings = self.load_settings()
        self._active_session_cache = {
            "mtime_ns": 0,
            "size": 0,
            "has_session": False,
            "sub_id": None,
            "username_hint": ""
        }
        self._sub_cache = {}

    def load_settings(self) -> AppSettings:
        """Load settings from settings.json or create default, syncing Windows autostart."""
        settings = AppSettings()
        if Config.SETTINGS_FILE.is_file():
            try:
                with open(Config.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    settings = AppSettings(**data)
            except Exception as e:
                logger.warning(f"Failed to load settings: {e}")

        # Sync autostart status from Windows registry
        settings.start_with_windows = is_autostart_enabled()

        # Auto-detect Riot Client path if unset
        if not settings.riot_client_path:
            detected = Config.find_riot_client_path()
            if detected:
                settings.riot_client_path = str(detected)

        self.save_settings(settings)
        return settings

    def save_settings(self, settings: AppSettings):
        """Persist settings to settings.json atomically and sync autostart."""
        self.settings = settings
        _write_json_atomic(Config.SETTINGS_FILE, settings.model_dump())
        set_autostart(settings.start_with_windows)
        logger.info("Application settings saved.")

    def get_accounts(self) -> List[AccountProfile]:
        """Load all registered account profiles with pinned accounts first."""
        accounts = []
        if not Config.PROFILES_DIR.exists():
            return accounts

        for profile_dir in Config.PROFILES_DIR.iterdir():
            if profile_dir.is_dir():
                meta_file = profile_dir / "profile.json"
                if meta_file.is_file():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            accounts.append(AccountProfile(**data))
                    except Exception:
                        continue

        # Sort accounts: Pinned accounts on top, then most recently used
        accounts.sort(
            key=lambda acc: (1 if getattr(acc, "is_pinned", False) else 0, acc.last_used or acc.created_at),
            reverse=True
        )
        return accounts

    def get_account(self, account_id: str) -> Optional[AccountProfile]:
        """Fetch a single account profile by ID."""
        profile_file = self.get_account_dir(account_id) / "profile.json"
        if profile_file.is_file():
            try:
                with open(profile_file, "r", encoding="utf-8") as f:
                    return AccountProfile(**json.load(f))
            except Exception:
                pass
        return None

    def mark_account_reauth(self, account_id: str, needs_reauth: bool = True):
        """Mark an account as requiring re-authentication or restored."""
        account = self.get_account(account_id)
        if account:
            account.needs_reauth = needs_reauth
            self.update_account_metadata(account)

    def get_account_dir(self, account_id: str) -> Path:
        return Config.PROFILES_DIR / account_id

    def invalidate_session_cache(self):
        """Invalidate in-memory cache when session files are swapped or cleaned."""
        self._active_session_cache = {
            "mtime_ns": 0,
            "size": 0,
            "has_session": False,
            "sub_id": None,
            "username_hint": ""
        }

    def _get_active_session_info(self) -> dict:
        """
        Fast cached inspection of Riot Client's active session.
        Checks file mtime & size before doing any disk reading or YAML parsing.
        """
        main_settings = Config.RIOT_LOCAL_DIR / "Riot Client" / "Data" / "RiotGamesPrivateSettings.yaml"
        if not main_settings.is_file():
            self._active_session_cache = {
                "mtime_ns": 0,
                "size": 0,
                "has_session": False,
                "sub_id": None,
                "username_hint": ""
            }
            return self._active_session_cache

        try:
            stat = main_settings.stat()
            mtime_ns = stat.st_mtime_ns
            size = stat.st_size
        except OSError:
            return self._active_session_cache

        if mtime_ns == self._active_session_cache["mtime_ns"] and size == self._active_session_cache["size"]:
            return self._active_session_cache

        has_session = False
        sub_id = None
        username_hint = ""

        try:
            with open(main_settings, "r", encoding="utf-8", errors="ignore") as f:
                data = yaml.safe_load(f) or {}

                riot_login = data.get("riot-login")
                if isinstance(riot_login, dict) and riot_login.get("persist") is not None:
                    has_session = True

                psl = data.get("psl")
                if isinstance(psl, dict):
                    auth = psl.get("authorization")
                    if isinstance(auth, dict) and auth.get("riot-client") is not None:
                        has_session = True

                rso = data.get("rso-authenticator")
                if isinstance(rso, dict):
                    for k in rso.keys():
                        if k != "tdid":
                            has_session = True
                            break

                id_token = data.get("psl", {}).get("authorization", {}).get("riot-client", {}).get("id_token")
                if id_token:
                    import base64
                    parts = id_token.split(".")
                    if len(parts) >= 2:
                        payload_b64 = parts[1]
                        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                        payload_bytes = base64.urlsafe_b64decode(payload_b64)
                        payload = json.loads(payload_bytes.decode("utf-8", errors="ignore"))
                        sub_id = payload.get("sub")
                        acct = payload.get("acct", {})
                        game_name = acct.get("game_name")
                        tag_line = acct.get("tag_line")
                        if game_name and tag_line:
                            username_hint = f"{game_name}#{tag_line}"
                        elif game_name:
                            username_hint = game_name
        except Exception:
            pass

        self._active_session_cache = {
            "mtime_ns": mtime_ns,
            "size": size,
            "has_session": has_session,
            "sub_id": sub_id,
            "username_hint": username_hint
        }
        return self._active_session_cache

    def has_active_riot_session(self) -> bool:
        """
        Check if Riot Client currently has an active logged-in session.
        Uses mtime-cached inspection for near-zero CPU usage.
        """
        return self._get_active_session_info()["has_session"]

    def extract_session_username_hint(self) -> str:
        """Attempt to extract username/alias hint from RiotGamesPrivateSettings.yaml."""
        return self._get_active_session_info()["username_hint"]

    def save_current_account(
        self,
        name: str,
        tag: str = "Main",
        color: str = "#ff4655",
        preferred_game: str = "riot_client",
        username_hint: str = "",
        notes: str = ""
    ) -> AccountProfile:
        """
        Snapshot the currently logged-in Riot session as a new saved account.
        """
        if not self.has_active_riot_session():
            raise RuntimeError(
                "No active Riot session found!\n"
                "Please open Riot Client, log into your account with 'Stay signed in' checked, then try again."
            )

        session_info = self._get_active_session_info()
        account = AccountProfile(
            name=name,
            tag=tag,
            color=color,
            preferred_game=preferred_game,
            username_hint=username_hint or session_info.get("username_hint") or "",
            sub_id=session_info.get("sub_id"),
            notes=notes
        )
        account.mark_used()

        profile_dir = self.get_account_dir(account.id)
        files_dir = profile_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        # 1. Copy session files
        for rel_file in Config.SESSION_FILES:
            src_file = Config.RIOT_LOCAL_DIR / rel_file
            if src_file.is_file():
                dest_file = files_dir / rel_file
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest_file)

        # 2. Copy session directories (like Sessions UUID folders)
        for rel_dir in Config.SESSION_DIRS:
            src_dir = Config.RIOT_LOCAL_DIR / rel_dir
            if src_dir.is_dir():
                dest_dir = files_dir / rel_dir
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                shutil.copytree(src_dir, dest_dir)

        # 3. Save profile metadata atomically
        _write_json_atomic(profile_dir / "profile.json", account.model_dump())
        logger.info(f"Saved new account profile '{account.name}' ({account.id})")
        return account

    def update_account_session(self, account_id: str):
        """
        Update an existing account's saved session with the currently active session.
        Useful when password or 2FA was refreshed.
        """
        if not self.has_active_riot_session():
            raise RuntimeError("No active Riot session found on this machine to update from.")

        profile_dir = self.get_account_dir(account_id)
        if not profile_dir.is_dir():
            raise FileNotFoundError("Account profile not found.")

        files_dir = profile_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        for rel_file in Config.SESSION_FILES:
            src_file = Config.RIOT_LOCAL_DIR / rel_file
            if src_file.is_file():
                dest_file = files_dir / rel_file
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest_file)

        for rel_dir in Config.SESSION_DIRS:
            src_dir = Config.RIOT_LOCAL_DIR / rel_dir
            if src_dir.is_dir():
                dest_dir = files_dir / rel_dir
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                shutil.copytree(src_dir, dest_dir)

        session_info = self._get_active_session_info()
        meta_file = profile_dir / "profile.json"
        with open(meta_file, "r", encoding="utf-8") as f:
            account = AccountProfile(**json.load(f))
        account.mark_used()
        account.needs_reauth = False
        if session_info.get("sub_id"):
            account.sub_id = session_info.get("sub_id")
        if not account.username_hint and session_info.get("username_hint"):
            account.username_hint = session_info.get("username_hint")
        _write_json_atomic(meta_file, account.model_dump())
        logger.info(f"Updated session tokens for '{account.name}' ({account.id})")

    def update_account_metadata(self, account: AccountProfile):
        """Save updated account metadata atomically (name, tag, color, notes, is_pinned)."""
        profile_dir = self.get_account_dir(account.id)
        if not profile_dir.is_dir():
            raise FileNotFoundError("Account profile not found.")
        meta_file = profile_dir / "profile.json"
        _write_json_atomic(meta_file, account.model_dump())

    def toggle_pin_account(self, account_id: str) -> bool:
        """Toggle pinned status for an account profile. Pinned accounts stay at the top."""
        account = self.get_account(account_id)
        if account:
            account.is_pinned = not getattr(account, "is_pinned", False)
            self.update_account_metadata(account)
            logger.info(f"Toggled pin on account '{account.name}': {account.is_pinned}")
            return account.is_pinned
        return False

    def export_accounts(self, target_zip: Path) -> int:
        """
        Export all saved accounts and settings to a portable ZIP archive.
        Returns the number of accounts exported.
        """
        accounts = self.get_accounts()
        target_zip.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            if Config.SETTINGS_FILE.is_file():
                zf.write(Config.SETTINGS_FILE, arcname="settings.json")

            for acc in accounts:
                profile_dir = self.get_account_dir(acc.id)
                if profile_dir.is_dir():
                    count += 1
                    for root, _, files in os.walk(profile_dir):
                        for file in files:
                            full_p = Path(root) / file
                            rel_p = full_p.relative_to(Config.APP_DATA_DIR)
                            zf.write(full_p, arcname=str(rel_p))

        logger.info(f"Exported {count} accounts to {target_zip}")
        return count

    def import_accounts(self, source_zip: Path) -> int:
        """
        Import accounts from a ZIP archive backup.
        Merges profiles cleanly without corrupting existing profiles.
        Returns the number of profiles imported.
        """
        if not source_zip.is_file():
            raise FileNotFoundError(f"Backup file not found: {source_zip}")

        imported_count = 0
        Config.ensure_directories()

        with zipfile.ZipFile(source_zip, "r") as zf:
            names = zf.namelist()
            for name in names:
                # Security check against path traversal
                if ".." in name or name.startswith("/") or name.startswith("\\"):
                    continue

                if name.startswith("profiles/") and name.endswith("profile.json"):
                    imported_count += 1

                target_path = Config.APP_DATA_DIR / name
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

        self.invalidate_session_cache()
        logger.info(f"Imported {imported_count} accounts from {source_zip}")
        return imported_count

    def switch_to_account(
        self,
        account_id: str,
        launch_product: Optional[str] = None,
        auto_launch: Optional[bool] = None
    ) -> bool:
        """
        Switch to the specified account:
        1. Ensure Riot launcher is closed to release file locks
        2. Safely swap session files with rollback protection
        3. Launch official Riot Client cleanly (zero game tampering)
        """
        profile_dir = self.get_account_dir(account_id)
        files_dir = profile_dir / "files"
        meta_file = profile_dir / "profile.json"

        if not files_dir.is_dir() or not meta_file.is_file():
            raise FileNotFoundError("Account profile files not found.")

        with open(meta_file, "r", encoding="utf-8") as f:
            account = AccountProfile(**json.load(f))

        # 1. Close only Riot Client launcher if running
        if ProcessManager.is_riot_running():
            ProcessManager.close_riot_client_launcher(timeout=4.0)

        # 2. Stage current session into a temporary backup directory for rollback
        backup_dir = Config.APP_DATA_DIR / ".session_swap_backup"
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            for rel_file in Config.SESSION_FILES:
                src = Config.RIOT_LOCAL_DIR / rel_file
                if src.is_file():
                    dest = backup_dir / rel_file
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)

            for rel_dir in Config.SESSION_DIRS:
                src_d = Config.RIOT_LOCAL_DIR / rel_dir
                if src_d.is_dir():
                    dest_d = backup_dir / rel_dir
                    shutil.copytree(src_d, dest_d)

            # 3. Clear active session files in %LOCALAPPDATA%/Riot Games
            for rel_file in Config.SESSION_FILES:
                target = Config.RIOT_LOCAL_DIR / rel_file
                if target.is_file():
                    try:
                        target.unlink()
                    except OSError:
                        pass

            for rel_dir in Config.SESSION_DIRS:
                target_dir = Config.RIOT_LOCAL_DIR / rel_dir
                if target_dir.is_dir():
                    try:
                        shutil.rmtree(target_dir, ignore_errors=True)
                    except OSError:
                        pass

            # 4. Restore target account's session files
            for rel_file in Config.SESSION_FILES:
                src_file = files_dir / rel_file
                if src_file.is_file():
                    dest_file = Config.RIOT_LOCAL_DIR / rel_file
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_file)

            for rel_dir in Config.SESSION_DIRS:
                src_dir = files_dir / rel_dir
                if src_dir.is_dir():
                    dest_dir = Config.RIOT_LOCAL_DIR / rel_dir
                    dest_dir.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(src_dir, dest_dir)

            # Swap succeeded: clean up temporary backup
            shutil.rmtree(backup_dir, ignore_errors=True)

        except Exception as swap_err:
            # Rollback previous session files from backup
            for rel_file in Config.SESSION_FILES:
                bak_f = backup_dir / rel_file
                if bak_f.is_file():
                    dest_f = Config.RIOT_LOCAL_DIR / rel_file
                    dest_f.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(bak_f, dest_f)
            for rel_dir in Config.SESSION_DIRS:
                bak_d = backup_dir / rel_dir
                if bak_d.is_dir():
                    dest_d = Config.RIOT_LOCAL_DIR / rel_dir
                    dest_d.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(bak_d, dest_d)
            shutil.rmtree(backup_dir, ignore_errors=True)
            raise RuntimeError(f"Session swap failed and was safely rolled back: {swap_err}")

        # 5. Update last_used timestamp & invalidate active cache
        account.mark_used()
        self.invalidate_session_cache()
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(account.model_dump(), f, indent=2)

        # 6. Launch Riot Client cleanly if requested
        should_launch = auto_launch if auto_launch is not None else self.settings.auto_launch
        if should_launch:
            exe_path = Path(self.settings.riot_client_path or "")
            if not exe_path.is_file():
                detected = Config.find_riot_client_path()
                if detected:
                    exe_path = detected
                    self.settings.riot_client_path = str(detected)
                    self.save_settings(self.settings)

            if exe_path.is_file():
                ProcessManager.launch(exe_path, product="riot_client")

        return True

    def prepare_new_login(self) -> bool:
        """
        Close Riot Client and clear the local session files so Riot Client
        boots with a fresh sign-in prompt for adding a new account,
        WITHOUT revoking previously saved account tokens on Riot's server.
        """
        ProcessManager.close_all_riot_processes(timeout=4.0)

        for rel_file in Config.SESSION_FILES:
            target = Config.RIOT_LOCAL_DIR / rel_file
            if target.is_file():
                try:
                    target.unlink()
                except OSError:
                    pass

        for rel_dir in Config.SESSION_DIRS:
            target_dir = Config.RIOT_LOCAL_DIR / rel_dir
            if target_dir.is_dir():
                try:
                    shutil.rmtree(target_dir, ignore_errors=True)
                except OSError:
                    pass

        self.invalidate_session_cache()
        exe_path = Path(self.settings.riot_client_path or "")
        if not exe_path.is_file():
            detected = Config.find_riot_client_path()
            if detected:
                exe_path = detected

        if exe_path.is_file():
            ProcessManager.launch(exe_path, product="riot_client")
            return True
        return False

    def delete_account(self, account_id: str):
        """Remove account profile directory completely."""
        profile_dir = self.get_account_dir(account_id)
        if profile_dir.is_dir():
            shutil.rmtree(profile_dir, ignore_errors=True)

    def get_account_sub_id(self, yaml_path: Path) -> Optional[str]:
        """Extract permanent Riot account subject UUID from id_token with caching."""
        if not yaml_path.is_file():
            return None
        try:
            stat = yaml_path.stat()
            cache_key = (str(yaml_path), stat.st_mtime_ns, stat.st_size)
            if cache_key in self._sub_cache:
                return self._sub_cache[cache_key]
        except OSError:
            pass

        sub = None
        try:
            import base64
            with open(yaml_path, "r", encoding="utf-8", errors="ignore") as f:
                data = yaml.safe_load(f) or {}
                id_token = data.get("psl", {}).get("authorization", {}).get("riot-client", {}).get("id_token")
                if id_token:
                    parts = id_token.split(".")
                    if len(parts) >= 2:
                        payload_b64 = parts[1]
                        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8", errors="ignore"))
                        sub = payload.get("sub")
        except Exception:
            pass

        try:
            stat = yaml_path.stat()
            self._sub_cache[(str(yaml_path), stat.st_mtime_ns, stat.st_size)] = sub
        except Exception:
            pass

        return sub

    def get_active_account_id(self) -> Optional[str]:
        """
        Determine which account is currently active by comparing permanent account IDs.
        Uses in-memory sub_id caching to avoid re-parsing YAML files.
        """
        info = self._get_active_session_info()
        if not info["has_session"] or not info["sub_id"]:
            return None

        cur_sub = info["sub_id"]

        for account in self.get_accounts():
            if account.needs_reauth:
                continue

            # Fast path: check cached sub_id in account model
            if account.sub_id:
                if account.sub_id == cur_sub:
                    return account.id
                continue

            # Fallback path for legacy profiles: extract sub_id once and persist it
            saved_file = self.get_account_dir(account.id) / "files" / "Riot Client" / "Data" / "RiotGamesPrivateSettings.yaml"
            sub = self.get_account_sub_id(saved_file)
            if sub:
                account.sub_id = sub
                self.update_account_metadata(account)
                if sub == cur_sub:
                    return account.id

        return None
