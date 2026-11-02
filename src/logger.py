"""
Structured file and console logger for Riot Link.
Writes rotating logs to %APPDATA%/RiotLink/logs/riotlink.log.
"""

import sys
import logging
from logging.handlers import RotatingFileHandler
from .config import Config

_initialized = False


def setup_logger():
    global _initialized
    if _initialized:
        return logging.getLogger("RiotLink")
    _initialized = True

    Config.ensure_directories()
    log_file = Config.LOGS_DIR / "riotlink.log"

    root_logger = logging.getLogger("RiotLink")
    root_logger.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Rotating file handler (up to 2MB, keeps 3 backups)
    try:
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
    except Exception:
        pass

    # Console stream handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    return root_logger


def get_logger(name: str = "RiotLink"):
    setup_logger()
    return logging.getLogger(f"RiotLink.{name}")


logger = get_logger("App")

