"""
CustomTkinter dialogs and modal windows for Riot Account Switcher.
"""

from typing import Callable
from tkinter import filedialog, messagebox
import customtkinter as ctk

from ..theme import Theme
from ...models import AccountProfile, AppSettings
from ...config import Config


class AddAccountModal(ctk.CTkToplevel):
    def __init__(self, parent, on_save: Callable[[str, str, str, str], None]):
        super().__init__(parent)
        self.on_save = on_save
        self.title("Save Current Riot Account")
        self.geometry("480x520")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_DARK)
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 480) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 520) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self._build_ui()

    def _build_ui(self):
        # Header banner
        header = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        title = ctk.CTkLabel(
            header,
            text="SAVE CURRENT ACCOUNT",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        title.pack(anchor="w", padx=24, pady=(16, 4))

        subtitle = ctk.CTkLabel(
            header,
            text="Captures the active session token from your official Riot Client.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_SECONDARY
        )
        subtitle.pack(anchor="w", padx=24, pady=(0, 16))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=20)

        # Account Name Field
        ctk.CTkLabel(
            content,
            text="ACCOUNT NAME / LABEL",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        self.name_entry = ctk.CTkEntry(
            content,
            placeholder_text="e.g. Main (EUW), Smurf Ranked, Valorant Alt...",
            height=38,
            fg_color=Theme.SURFACE,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.TEXT_PRIMARY,
            placeholder_text_color=Theme.TEXT_MUTED
        )
        self.name_entry.pack(fill="x", pady=(0, 16))
        self.name_entry.focus()

        # Tag Field
        ctk.CTkLabel(
            content,
            text="TAG / CATEGORY",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        self.tag_menu = ctk.CTkOptionMenu(
            content,
            values=Theme.TAG_OPTIONS,
            height=36,
            fg_color=Theme.SURFACE,
            button_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.tag_menu.set("Main")
        self.tag_menu.pack(fill="x", pady=(0, 16))

        # Preferred Game to Launch
        ctk.CTkLabel(
            content,
            text="DEFAULT GAME TO LAUNCH",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        game_names = {k: v["name"] for k, v in Config.PRODUCTS.items()}
        self.game_keys = list(Config.PRODUCTS.keys())
        self.game_labels = list(game_names.values())

        self.game_menu = ctk.CTkOptionMenu(
            content,
            values=self.game_labels,
            height=36,
            fg_color=Theme.SURFACE,
            button_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.game_menu.set("League of Legends")
        self.game_menu.pack(fill="x", pady=(0, 16))

        # Color Accent Choice
        ctk.CTkLabel(
            content,
            text="CARD COLOR ACCENT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 6))

        color_frame = ctk.CTkFrame(content, fg_color="transparent")
        color_frame.pack(fill="x", pady=(0, 20))

        self.selected_color = ctk.StringVar(value="#ff4655")
        for hex_code, label in Theme.AVATAR_COLORS:
            rb = ctk.CTkRadioButton(
                color_frame,
                text="",
                value=hex_code,
                variable=self.selected_color,
                width=24,
                radiobutton_width=20,
                radiobutton_height=20,
                fg_color=hex_code,
                border_color=hex_code,
                hover_color=hex_code
            )
            rb.pack(side="left", padx=4)

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 20))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_SECONDARY,
            height=40,
            command=self.destroy
        )
        cancel_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save Account Profile",
            fg_color=Theme.ACCENT_RED,
            hover_color=Theme.ACCENT_RED_HOVER,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=40,
            command=self._handle_save
        )
        save_btn.pack(side="right", expand=True, fill="x", padx=(8, 0))

    def _handle_save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Name Required", "Please enter a name for this account profile.", parent=self)
            return

        tag = self.tag_menu.get()
        selected_game_label = self.game_menu.get()
        game_key = "riot_client"
        for k, v in Config.PRODUCTS.items():
            if v["name"] == selected_game_label:
                game_key = k
                break

        color = self.selected_color.get()
        self.destroy()
        self.on_save(name, tag, color, game_key)


class EditAccountModal(ctk.CTkToplevel):
    def __init__(self, parent, account: AccountProfile, on_save: Callable[[AccountProfile], None]):
        super().__init__(parent)
        self.account = account
        self.on_save = on_save
        self.title("Edit Account Profile")
        self.geometry("480x520")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_DARK)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 480) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 520) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self._build_ui()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        title = ctk.CTkLabel(
            header,
            text="EDIT ACCOUNT PROFILE",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        title.pack(anchor="w", padx=24, pady=(16, 4))

        subtitle = ctk.CTkLabel(
            header,
            text=f"Editing profile for {self.account.name} ({self.account.username_hint or 'Riot Account'})",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_SECONDARY
        )
        subtitle.pack(anchor="w", padx=24, pady=(0, 16))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=20)

        # Account Name
        ctk.CTkLabel(
            content,
            text="ACCOUNT NAME / LABEL",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        self.name_entry = ctk.CTkEntry(
            content,
            height=38,
            fg_color=Theme.SURFACE,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.name_entry.insert(0, self.account.name)
        self.name_entry.pack(fill="x", pady=(0, 16))
        self.name_entry.focus()

        # Tag
        ctk.CTkLabel(
            content,
            text="TAG / CATEGORY",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        self.tag_menu = ctk.CTkOptionMenu(
            content,
            values=Theme.TAG_OPTIONS,
            height=36,
            fg_color=Theme.SURFACE,
            button_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.tag_menu.set(self.account.tag if self.account.tag in Theme.TAG_OPTIONS else "Main")
        self.tag_menu.pack(fill="x", pady=(0, 16))

        # Preferred Game
        ctk.CTkLabel(
            content,
            text="DEFAULT GAME TO LAUNCH",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        game_names = {k: v["name"] for k, v in Config.PRODUCTS.items()}
        current_game_name = game_names.get(self.account.preferred_game, "Riot Client")

        self.game_menu = ctk.CTkOptionMenu(
            content,
            values=list(game_names.values()),
            height=36,
            fg_color=Theme.SURFACE,
            button_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.game_menu.set(current_game_name)
        self.game_menu.pack(fill="x", pady=(0, 16))

        # Color Accent
        ctk.CTkLabel(
            content,
            text="CARD COLOR ACCENT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 6))

        color_frame = ctk.CTkFrame(content, fg_color="transparent")
        color_frame.pack(fill="x", pady=(0, 20))

        self.selected_color = ctk.StringVar(value=self.account.color or "#ff4655")
        for hex_code, label in Theme.AVATAR_COLORS:
            rb = ctk.CTkRadioButton(
                color_frame,
                text="",
                value=hex_code,
                variable=self.selected_color,
                width=24,
                radiobutton_width=20,
                radiobutton_height=20,
                fg_color=hex_code,
                border_color=hex_code,
                hover_color=hex_code
            )
            rb.pack(side="left", padx=4)

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 20))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_SECONDARY,
            height=40,
            command=self.destroy
        )
        cancel_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save Changes",
            fg_color=Theme.ACCENT_CYAN,
            hover_color=Theme.ACCENT_CYAN_HOVER,
            text_color="#000000",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=40,
            command=self._handle_save
        )
        save_btn.pack(side="right", expand=True, fill="x", padx=(8, 0))

    def _handle_save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Name Required", "Please enter an account name.", parent=self)
            return

        tag = self.tag_menu.get()
        selected_game_label = self.game_menu.get()
        game_key = "riot_client"
        for k, v in Config.PRODUCTS.items():
            if v["name"] == selected_game_label:
                game_key = k
                break

        self.account.name = name
        self.account.tag = tag
        self.account.color = self.selected_color.get()
        self.account.preferred_game = game_key

        self.destroy()
        self.on_save(self.account)


class SettingsModal(ctk.CTkToplevel):
    def __init__(self, parent, settings: AppSettings, on_save: Callable[[AppSettings], None]):
        super().__init__(parent)
        self.settings = settings
        self.on_save = on_save
        self.title("Application Settings")
        self.geometry("520x420")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_DARK)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 520) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 420) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self._build_ui()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            header,
            text="APPLICATION SETTINGS",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=24, pady=(16, 4))

        ctk.CTkLabel(
            header,
            text="Configure Riot Client executable location and launch behavior.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", padx=24, pady=(0, 16))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=20)

        # Riot Client Path
        ctk.CTkLabel(
            content,
            text="RIOT CLIENT PATH (RiotClientServices.exe)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        path_row = ctk.CTkFrame(content, fg_color="transparent")
        path_row.pack(fill="x", pady=(0, 16))

        self.path_entry = ctk.CTkEntry(
            path_row,
            height=36,
            fg_color=Theme.SURFACE,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        if self.settings.riot_client_path:
            self.path_entry.insert(0, self.settings.riot_client_path)

        browse_btn = ctk.CTkButton(
            path_row,
            text="Browse...",
            width=80,
            height=36,
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            command=self._browse_path
        )
        browse_btn.pack(side="right")

        # Auto Launch Checkbox
        self.auto_launch_var = ctk.BooleanVar(value=self.settings.auto_launch)
        self.auto_launch_cb = ctk.CTkCheckBox(
            content,
            text="Automatically launch game / client immediately after switching",
            variable=self.auto_launch_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_PRIMARY,
            fg_color=Theme.ACCENT_CYAN,
            hover_color=Theme.ACCENT_CYAN_HOVER
        )
        self.auto_launch_cb.pack(anchor="w", pady=(8, 16))

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 20))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_SECONDARY,
            height=40,
            command=self.destroy
        )
        cancel_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save Settings",
            fg_color=Theme.ACCENT_CYAN,
            hover_color=Theme.ACCENT_CYAN_HOVER,
            text_color="#000000",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=40,
            command=self._handle_save
        )
        save_btn.pack(side="right", expand=True, fill="x", padx=(8, 0))

    def _browse_path(self):
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Select RiotClientServices.exe",
            filetypes=[("RiotClientServices.exe", "RiotClientServices.exe"), ("Executable Files", "*.exe")]
        )
        if file_path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, file_path)

    def _handle_save(self):
        path_val = self.path_entry.get().strip()
        self.settings.riot_client_path = path_val or None
        self.settings.auto_launch = self.auto_launch_var.get()
        self.destroy()
        self.on_save(self.settings)


class GuideModal(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("How to Add & Switch Accounts")
        self.geometry("540x580")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_DARK)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 540) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 580) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self._build_ui()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            header,
            text="HOW TO ADD & SWITCH ACCOUNTS",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=24, pady=(16, 4))

        ctk.CTkLabel(
            header,
            text="Step-by-step guide to saving multiple accounts without passwords.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", padx=24, pady=(0, 16))

        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=16)

        steps = [
            (
                "1️⃣  Save Your First Account",
                "Open your official Riot Client, type your username and password, make sure 'Stay signed in' is CHECKED, and log in. Once you see the home screen, open this app and click '+ SAVE CURRENT ACCOUNT'."
            ),
            (
                "2️⃣  Adding Another Account (Important!)",
                "Do NOT click 'Sign Out' in Riot Client! Instead, click '🔑 LOG IN ANOTHER ACCOUNT' in this app. It opens a clean login window without disconnecting your first account. Log into Account #2 (with 'Stay signed in' checked) and click '+ SAVE CURRENT ACCOUNT'."
            ),
            (
                "3️⃣  1-Click Instant Switching",
                "Whenever you want to switch, just click 'SWITCH & PLAY' on any saved card. You can also click the 'LoL' or 'VAL' buttons to jump straight into League of Legends or VALORANT!"
            ),
            (
                "4️⃣  Manage Your Accounts",
                "Use the icon buttons on each card anytime:\n• ✏️ Edit: Change account nickname, tag, or avatar color\n• 🔄 Refresh: Renew / re-link session if needed\n• 🗑️ Delete: Remove an account profile"
            ),
            (
                "5️⃣  ⚠️ Never Click 'Sign Out' in Riot Client",
                "Clicking 'Sign Out' inside Riot Client tells Riot's servers to destroy your login token.\n\n"
                "• To switch accounts: Always switch directly in this app!\n"
                "• If an account is marked [LOGGED OUT]: Sign back in on Riot Client (check 'Stay signed in') and click the highlighted 🔄 (Refresh) button on its card to restore it!"
            ),
        ]

        for step_title, step_desc in steps:
            card = ctk.CTkFrame(content, fg_color=Theme.SURFACE, corner_radius=8, border_width=1, border_color=Theme.CARD_BORDER)
            card.pack(fill="x", pady=6)

            ctk.CTkLabel(
                card,
                text=step_title,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=Theme.ACCENT_CYAN
            ).pack(anchor="w", padx=14, pady=(10, 4))

            ctk.CTkLabel(
                card,
                text=step_desc,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=Theme.TEXT_SECONDARY,
                justify="left",
                wraplength=460
            ).pack(anchor="w", padx=14, pady=(0, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 18))

        got_it_btn = ctk.CTkButton(
            btn_frame,
            text="Got It, Let's Play!",
            fg_color=Theme.ACCENT_CYAN,
            hover_color=Theme.ACCENT_CYAN_HOVER,
            text_color="#000000",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=40,
            command=self.destroy
        )
        got_it_btn.pack(fill="x")
