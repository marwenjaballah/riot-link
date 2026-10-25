"""
Data models for Account Profiles and Application Settings.
"""

from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class AccountProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    username_hint: str = ""
    tag: str = "Main"
    color: str = "#ff4655"
    preferred_game: str = "riot_client"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_used: str | None = None
    notes: str = ""

    def mark_used(self):
        self.last_used = datetime.now().isoformat()


class AppSettings(BaseModel):
    riot_client_path: str | None = None
    auto_launch: bool = True
    default_game: str = "riot_client"
    close_after_launch: bool = False
    theme_mode: str = "dark"
