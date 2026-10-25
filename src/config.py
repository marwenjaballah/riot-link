"""
Configuration & Path Management for Riot Link.
"""

from pathlib import Path
import os
import sys
import shutil
import winreg
import psutil


class Config:
    APP_NAME = "Riot Link"
    APP_VERSION = "1.0.0"
    APP_TAGLINE = "1-Click Account Switcher • 2FA Persistent • 100% Anti-Cheat Safe"

    # Branding & Repository
    AUTHOR_NAME = "Marwen Jaballah"
    AUTHOR_GITHUB = "https://github.com/marwenjaballah"
    GITHUB_REPO = "marwenjaballah/riot-link"
    GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
    GITHUB_API_LATEST_RELEASE = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    # Application data directory (in %APPDATA%/RiotLink)
    APP_DATA_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "RiotLink"
    PROFILES_DIR = APP_DATA_DIR / "profiles"
    SETTINGS_FILE = APP_DATA_DIR / "settings.json"

    # Riot Local AppData Directories
    LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    RIOT_LOCAL_DIR = LOCAL_APPDATA / "Riot Games"
    RIOT_CLIENT_DATA_DIR = RIOT_LOCAL_DIR / "Riot Client" / "Data"
    RIOT_CLIENT_CONFIG_DIR = RIOT_LOCAL_DIR / "Riot Client" / "Config"
    RIOT_CLIENT_SESSIONS_DIR = RIOT_CLIENT_DATA_DIR / "Sessions"

    # Game-specific private settings
    LOL_DATA_DIR = RIOT_LOCAL_DIR / "League of Legends" / "Data"
    VALORANT_DATA_DIR = RIOT_LOCAL_DIR / "VALORANT" / "Data"

    # Files that must be backed up/swapped for full session persistence
    SESSION_FILES = [
        # Relative to %LOCALAPPDATA%/Riot Games
        Path("Riot Client/Data/RiotGamesPrivateSettings.yaml"),
        Path("Riot Client/Config/RiotClientSettings.yaml"),
        Path("League of Legends/Data/RiotGamesPrivateSettings.yaml"),
        Path("VALORANT/Data/RiotGamesPrivateSettings.yaml"),
    ]

    SESSION_DIRS = [
        Path("Riot Client/Data/Sessions"),
    ]

    # Target Riot Process Names to manage
    RIOT_PROCESS_NAMES = [
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

    # Product launch parameters
    PRODUCTS = {
        "riot_client": {
            "name": "Riot Client",
            "args": [],
            "icon": "riot",
        },
        "league_of_legends": {
            "name": "League of Legends",
            "args": ["--launch-product=league_of_legends", "--launch-patchline=live"],
            "icon": "lol",
        },
        "valorant": {
            "name": "VALORANT",
            "args": ["--launch-product=valorant", "--launch-patchline=live"],
            "icon": "valorant",
        },
        "teamfight_tactics": {
            "name": "Teamfight Tactics",
            "args": ["--launch-product=teamfight_tactics", "--launch-patchline=live"],
            "icon": "tft",
        },
    }

    @classmethod
    def get_assets_dir(cls) -> Path:
        """Locate assets directory across local source and PyInstaller frozen builds."""
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS) / "assets"
        return Path(__file__).resolve().parent.parent / "assets"

    @classmethod
    def ensure_directories(cls):
        """Ensure application directories exist."""
        cls.APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def find_riot_client_path(cls) -> Path | None:
        """
        Dynamically locate RiotClientServices.exe:
        1. Check running processes
        2. Check Windows Registry
        3. Check common drive paths (D:, C:, E:, etc.)
        """
        # 1. Check running process
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                name = proc.info.get("name") or ""
                if name.lower() == "riotclientservices.exe":
                    exe = proc.info.get("exe")
                    if exe and Path(exe).is_file():
                        return Path(exe)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 2. Check Windows Registry
        reg_paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Riot Games\RiotClient"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Riot Games, Inc\Riot Client"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Riot Games\Riot Client"),
        ]
        for root_key, sub_key in reg_paths:
            try:
                with winreg.OpenKey(root_key, sub_key) as key:
                    for val_name in ["Path", "InstallPath", "Location"]:
                        try:
                            val, _ = winreg.QueryValueEx(key, val_name)
                            p = Path(val)
                            if p.name.lower() != "riotclientservices.exe":
                                p = p / "RiotClientServices.exe"
                            if p.is_file():
                                return p
                        except FileNotFoundError:
                            pass
            except (FileNotFoundError, OSError):
                pass

        # 3. Check common known locations
        candidates = [
            Path("D:/Riot Games/Riot Client/RiotClientServices.exe"),
            Path("C:/Riot Games/Riot Client/RiotClientServices.exe"),
            Path("E:/Riot Games/Riot Client/RiotClientServices.exe"),
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Riot Client" / "RiotClientServices.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate

        return None
