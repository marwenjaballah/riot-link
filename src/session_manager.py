"""
Session Manager for backing up, restoring, and switching Riot Client account sessions.
"""

import json
import shutil
import hashlib
from pathlib import Path
from typing import List, Optional
import yaml

from .config import Config
from .models import AccountProfile, AppSettings
from .process_manager import ProcessManager


class SessionManager:
    def __init__(self):
        Config.ensure_directories()
        self.settings = self.load_settings()

    def load_settings(self) -> AppSettings:
        """Load settings from settings.json or create default."""
        if Config.SETTINGS_FILE.is_file():
            try:
                with open(Config.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return AppSettings(**data)
            except Exception:
                pass
        settings = AppSettings()
        # Auto-detect Riot Client path if unset
        detected = Config.find_riot_client_path()
        if detected:
            settings.riot_client_path = str(detected)
        self.save_settings(settings)
        return settings

    def save_settings(self, settings: AppSettings):
        """Persist settings to settings.json."""
        self.settings = settings
        with open(Config.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings.model_dump(), f, indent=2)

    def get_accounts(self) -> List[AccountProfile]:
        """Load all registered account profiles."""
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

        # Sort accounts: most recently used first
        accounts.sort(key=lambda acc: acc.last_used or acc.created_at, reverse=True)
        return accounts

    def get_account_dir(self, account_id: str) -> Path:
        return Config.PROFILES_DIR / account_id

    def has_active_riot_session(self) -> bool:
        """
        Check if Riot Client currently has an active logged-in session.
        Validates that riot-login: persist or psl authorization is not null.
        """
        main_settings = Config.RIOT_LOCAL_DIR / "Riot Client" / "Data" / "RiotGamesPrivateSettings.yaml"
        if not main_settings.is_file():
            return False
        try:
            with open(main_settings, "r", encoding="utf-8", errors="ignore") as f:
                data = yaml.safe_load(f) or {}
                persist = data.get("riot-login", {}).get("persist")
                psl = data.get("psl", {}).get("authorization", {}).get("riot-client")
                rso = data.get("rso-authenticator", {})

                if persist is not None or psl is not None:
                    return True
                if isinstance(rso, dict):
                    # If any key other than tdid exists (e.g. session tokens)
                    for k in rso.keys():
                        if k != "tdid":
                            return True
        except Exception:
            pass
        return False

    def extract_session_username_hint(self) -> str:
        """Attempt to extract username/alias hint from RiotGamesPrivateSettings.yaml."""
        import base64
        main_yaml = Config.RIOT_LOCAL_DIR / "Riot Client" / "Data" / "RiotGamesPrivateSettings.yaml"
        if not main_yaml.is_file():
            return ""
        try:
            with open(main_yaml, "r", encoding="utf-8", errors="ignore") as f:
                data = yaml.safe_load(f) or {}
                id_token = data.get("psl", {}).get("authorization", {}).get("riot-client", {}).get("id_token")
                if id_token:
                    parts = id_token.split(".")
                    if len(parts) >= 2:
                        payload_b64 = parts[1]
                        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                        payload_bytes = base64.urlsafe_b64decode(payload_b64)
                        payload = json.loads(payload_bytes.decode("utf-8", errors="ignore"))
                        acct = payload.get("acct", {})
                        game_name = acct.get("game_name")
                        tag_line = acct.get("tag_line")
                        if game_name and tag_line:
                            return f"{game_name}#{tag_line}"
                        if game_name:
                            return game_name
        except Exception:
            pass
        return ""

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

        account = AccountProfile(
            name=name,
            tag=tag,
            color=color,
            preferred_game=preferred_game,
            username_hint=username_hint or self.extract_session_username_hint(),
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

        # 3. Save profile metadata
        with open(profile_dir / "profile.json", "w", encoding="utf-8") as f:
            json.dump(account.model_dump(), f, indent=2)

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

        meta_file = profile_dir / "profile.json"
        with open(meta_file, "r", encoding="utf-8") as f:
            account = AccountProfile(**json.load(f))
        account.mark_used()
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(account.model_dump(), f, indent=2, ensure_ascii=False)

    def update_account_metadata(self, account: AccountProfile):
        """Save updated account metadata (name, tag, color, preferred_game, notes)."""
        profile_dir = self.get_account_dir(account.id)
        if not profile_dir.is_dir():
            raise FileNotFoundError("Account profile not found.")
        meta_file = profile_dir / "profile.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(account.model_dump(), f, indent=2, ensure_ascii=False)

    def switch_to_account(
        self,
        account_id: str,
        launch_product: Optional[str] = None,
        auto_launch: Optional[bool] = None
    ) -> bool:
        """
        Switch to the specified account:
        1. Close Riot processes cleanly
        2. Replace active session files with the target account's session
        3. Launch Riot Client or chosen game
        """
        profile_dir = self.get_account_dir(account_id)
        files_dir = profile_dir / "files"
        meta_file = profile_dir / "profile.json"

        if not files_dir.is_dir() or not meta_file.is_file():
            raise FileNotFoundError("Account profile files not found.")

        with open(meta_file, "r", encoding="utf-8") as f:
            account = AccountProfile(**json.load(f))

        # 1. Close all active Riot processes to unlock files
        ProcessManager.close_all_riot_processes(timeout=4.0)

        # 2. Clear current session files in %LOCALAPPDATA%/Riot Games
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

        # 3. Restore target account's session files
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

        # 4. Update last_used timestamp
        account.mark_used()
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(account.model_dump(), f, indent=2)

        # 5. Launch Riot Client or Game if requested
        should_launch = auto_launch if auto_launch is not None else self.settings.auto_launch
        if should_launch:
            product = launch_product or account.preferred_game or self.settings.default_game
            exe_path = Path(self.settings.riot_client_path or "")
            if not exe_path.is_file():
                detected = Config.find_riot_client_path()
                if detected:
                    exe_path = detected
                    self.settings.riot_client_path = str(detected)
                    self.save_settings(self.settings)

            if exe_path.is_file():
                ProcessManager.launch(exe_path, product=product)

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
        """Extract permanent Riot account subject UUID from id_token."""
        import base64
        if not yaml_path.is_file():
            return None
        try:
            with open(yaml_path, "r", encoding="utf-8", errors="ignore") as f:
                data = yaml.safe_load(f) or {}
                id_token = data.get("psl", {}).get("authorization", {}).get("riot-client", {}).get("id_token")
                if id_token:
                    parts = id_token.split(".")
                    if len(parts) >= 2:
                        payload_b64 = parts[1]
                        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8", errors="ignore"))
                        return payload.get("sub")
        except Exception:
            pass
        return None

    def get_active_account_id(self) -> Optional[str]:
        """
        Determine which account is currently active by comparing permanent account IDs.
        """
        current_file = Config.RIOT_LOCAL_DIR / "Riot Client" / "Data" / "RiotGamesPrivateSettings.yaml"
        cur_sub = self.get_account_sub_id(current_file)
        if not cur_sub:
            return None

        for account in self.get_accounts():
            saved_file = self.get_account_dir(account.id) / "files" / "Riot Client" / "Data" / "RiotGamesPrivateSettings.yaml"
            if self.get_account_sub_id(saved_file) == cur_sub:
                return account.id
        return None
