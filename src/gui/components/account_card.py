"""
Account Card component displaying profile info, quick actions, and status.
Uniform button sizing and crisp high-DPI icon assets.
"""

from pathlib import Path
from typing import Callable
from datetime import datetime
import customtkinter as ctk
from PIL import Image

from ..theme import Theme
from ...models import AccountProfile
from ...config import Config

# Cached CTkImages for action buttons
_edit_icon = None
_refresh_icon = None
_trash_icon = None


def get_action_icons():
    global _edit_icon, _refresh_icon, _trash_icon
    if _edit_icon is None:
        assets_dir = Config.get_assets_dir()
        img_e = Image.open(assets_dir / "icon_edit.png")
        img_r = Image.open(assets_dir / "icon_refresh.png")
        img_t = Image.open(assets_dir / "icon_trash.png")
        _edit_icon = ctk.CTkImage(light_image=img_e, dark_image=img_e, size=(16, 16))
        _refresh_icon = ctk.CTkImage(light_image=img_r, dark_image=img_r, size=(16, 16))
        _trash_icon = ctk.CTkImage(light_image=img_t, dark_image=img_t, size=(16, 16))
    return _edit_icon, _refresh_icon, _trash_icon


class AccountCard(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        account: AccountProfile,
        is_active: bool,
        on_switch: Callable[[str, str], None],
        on_edit: Callable[[AccountProfile], None],
        on_update_token: Callable[[str], None],
        on_delete: Callable[[str], None],
        **kwargs
    ):
        if account.needs_reauth:
            border_col = "#b45309"
            border_w = 2
        elif is_active:
            border_col = Theme.CARD_ACTIVE_BORDER
            border_w = 2
        else:
            border_col = Theme.CARD_BORDER
            border_w = 1

        super().__init__(
            parent,
            fg_color=Theme.CARD_BG,
            corner_radius=12,
            border_width=border_w,
            border_color=border_col,
            **kwargs
        )
        self.account = account
        self.is_active = is_active and not account.needs_reauth
        self.on_switch = on_switch
        self.on_edit = on_edit
        self.on_update_token = on_update_token
        self.on_delete = on_delete

        self._build_card()

    def _build_card(self):
        # Inner flex container
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        # 1. Left Avatar (Uniform 44x44)
        avatar_frame = ctk.CTkFrame(
            inner,
            width=44,
            height=44,
            corner_radius=22,
            fg_color=self.account.color or Theme.ACCENT_RED,
            border_width=2,
            border_color=Theme.CARD_ACTIVE_BORDER if self.is_active else Theme.CARD_BORDER
        )
        avatar_frame.pack(side="left", padx=(0, 12))
        avatar_frame.pack_propagate(False)

        initial = (self.account.name[:1] if self.account.name else "R").upper()
        avatar_label = ctk.CTkLabel(
            avatar_frame,
            text=initial,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#ffffff"
        )
        avatar_label.pack(expand=True)

        # 2. Middle Information Section (Flexibly expands)
        info_col = ctk.CTkFrame(inner, fg_color="transparent")
        info_col.pack(side="left", fill="both", expand=True)

        # Row 1: Name + Tag Pill + Active Badge
        top_row = ctk.CTkFrame(info_col, fg_color="transparent")
        top_row.pack(fill="x", anchor="w")

        name_lbl = ctk.CTkLabel(
            top_row,
            text=self.account.name,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        name_lbl.pack(side="left", padx=(0, 8))

        # Themed Tag Pill
        tag_text_col, tag_bg_col = Theme.TAG_STYLES.get(
            self.account.tag,
            ("#94a3b8", Theme.SURFACE)
        )
        tag_lbl = ctk.CTkLabel(
            top_row,
            text=f" {self.account.tag.upper()} ",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=tag_bg_col,
            text_color=tag_text_col,
            corner_radius=4,
            height=20
        )
        tag_lbl.pack(side="left", padx=(0, 8))

        # Status badges
        if self.account.needs_reauth:
            warn_badge = ctk.CTkLabel(
                top_row,
                text=" ⚠️ LOGGED OUT ",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                fg_color="#451a03",
                text_color="#fbbf24",
                corner_radius=4,
                height=20
            )
            warn_badge.pack(side="left")
        elif self.is_active:
            active_badge = ctk.CTkLabel(
                top_row,
                text=" ● ACTIVE ",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                fg_color="#064e3b",
                text_color="#34d399",
                corner_radius=4,
                height=20
            )
            active_badge.pack(side="left")

        # Row 2: Riot ID / Username hint & Game details
        bottom_row = ctk.CTkFrame(info_col, fg_color="transparent")
        bottom_row.pack(fill="x", anchor="w", pady=(3, 0))

        if self.account.needs_reauth:
            sub_lbl = ctk.CTkLabel(
                bottom_row,
                text="⚠️ Session revoked in Riot Client • Click 🔄 to re-link",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color="#f59e0b"
            )
            sub_lbl.pack(side="left")
        else:
            if self.account.username_hint:
                riot_id_lbl = ctk.CTkLabel(
                    bottom_row,
                    text=self.account.username_hint,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    text_color=Theme.ACCENT_CYAN
                )
                riot_id_lbl.pack(side="left", padx=(0, 6))

                sep_lbl = ctk.CTkLabel(
                    bottom_row,
                    text="•",
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    text_color=Theme.TEXT_MUTED
                )
                sep_lbl.pack(side="left", padx=(0, 6))

            game_name = Config.PRODUCTS.get(self.account.preferred_game, {}).get("name", "Riot Client")
            last_used_str = self._format_last_used(self.account.last_used)

            sub_text = f"Default: {game_name} • {last_used_str}"
            sub_lbl = ctk.CTkLabel(
                bottom_row,
                text=sub_text,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=Theme.TEXT_MUTED
            )
            sub_lbl.pack(side="left")

        # 3. Right Action Buttons: Uniform dimensions, pixel-perfect alignment
        actions_frame = ctk.CTkFrame(inner, fg_color="transparent")
        actions_frame.pack(side="right", padx=(8, 0))

        # Direct Game Buttons (LoL, VAL) - Height: 34
        lol_btn = ctk.CTkButton(
            actions_frame,
            text="LoL",
            width=40,
            height=34,
            corner_radius=6,
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.ACCENT_GOLD,
            border_width=1,
            border_color="#3b321c",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=lambda: self.on_switch(self.account.id, "league_of_legends")
        )
        lol_btn.pack(side="left", padx=2)

        val_btn = ctk.CTkButton(
            actions_frame,
            text="VAL",
            width=40,
            height=34,
            corner_radius=6,
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.ACCENT_RED,
            border_width=1,
            border_color="#421a22",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=lambda: self.on_switch(self.account.id, "valorant")
        )
        val_btn.pack(side="left", padx=2)

        # Primary Switch / Play button - EXACT width: 115, height: 34 on ALL cards!
        if self.account.needs_reauth:
            switch_btn_text = "RE-LOGIN"
            primary_fg = "#9a3412"
            primary_hover = "#c2410c"
            primary_text_col = "#ffffff"
        elif self.is_active:
            switch_btn_text = "PLAY"
            primary_fg = Theme.ACCENT_CYAN
            primary_hover = Theme.ACCENT_CYAN_HOVER
            primary_text_col = "#000000"
        else:
            switch_btn_text = "SWITCH & PLAY"
            primary_fg = Theme.ACCENT_RED
            primary_hover = Theme.ACCENT_RED_HOVER
            primary_text_col = "#ffffff"

        primary_btn = ctk.CTkButton(
            actions_frame,
            text=switch_btn_text,
            width=115,
            height=34,
            corner_radius=6,
            fg_color=primary_fg,
            hover_color=primary_hover,
            text_color=primary_text_col,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=lambda: self.on_switch(self.account.id, self.account.preferred_game)
        )
        primary_btn.pack(side="left", padx=(3, 6))

        # Crisp High-DPI Vector Icons (Uniform 34x34)
        edit_icon, refresh_icon, trash_icon = get_action_icons()

        # Icon Button 1: Edit Account (✏️)
        edit_btn = ctk.CTkButton(
            actions_frame,
            text="",
            image=edit_icon,
            width=34,
            height=34,
            corner_radius=6,
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            command=lambda: self.on_edit(self.account)
        )
        edit_btn.pack(side="left", padx=2)

        # Icon Button 2: Refresh Session Token (🔄) - Highlighted if needs reauth
        refresh_fg = "#78350f" if self.account.needs_reauth else Theme.SURFACE
        refresh_hover = "#92400e" if self.account.needs_reauth else Theme.SURFACE_HOVER
        refresh_border = "#d97706" if self.account.needs_reauth else Theme.CARD_BORDER

        refresh_btn = ctk.CTkButton(
            actions_frame,
            text="",
            image=refresh_icon,
            width=34,
            height=34,
            corner_radius=6,
            fg_color=refresh_fg,
            hover_color=refresh_hover,
            border_width=1,
            border_color=refresh_border,
            command=lambda: self.on_update_token(self.account.id)
        )
        refresh_btn.pack(side="left", padx=2)

        # Icon Button 3: Delete Account (🗑️)
        del_btn = ctk.CTkButton(
            actions_frame,
            text="",
            image=trash_icon,
            width=34,
            height=34,
            corner_radius=6,
            fg_color=Theme.SURFACE,
            hover_color="#451a1a",
            border_width=1,
            border_color=Theme.CARD_BORDER,
            command=lambda: self.on_delete(self.account.id)
        )
        del_btn.pack(side="left", padx=2)

    def _format_last_used(self, ts_str: str | None) -> str:
        if not ts_str:
            return "Never used"
        try:
            dt = datetime.fromisoformat(ts_str)
            now = datetime.now()
            diff = now - dt
            if diff.days == 0:
                if diff.seconds < 3600:
                    mins = max(1, diff.seconds // 60)
                    return f"{mins}m ago"
                hours = diff.seconds // 3600
                return f"{hours}h ago"
            elif diff.days == 1:
                return "Yesterday"
            elif diff.days < 7:
                return f"{diff.days}d ago"
            else:
                return dt.strftime("%b %d")
        except Exception:
            return "Recently"
