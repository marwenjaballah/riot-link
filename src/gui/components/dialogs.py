"""
CustomTkinter dialogs and modal windows for Riot Account Switcher.
"""

from typing import Callable, Optional
from tkinter import filedialog, messagebox
import webbrowser
import threading
import sys
import customtkinter as ctk

from ..theme import Theme
from ...models import AccountProfile, AppSettings
from ...config import Config


class AddAccountModal(ctk.CTkToplevel):
    def __init__(self, parent, on_save: Callable[[str, str, str, str, str], None]):
        super().__init__(parent)
        self.on_save = on_save
        self.title("Save Current Riot Account")
        self.geometry("480x510")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_DARK)
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 480) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 510) // 2
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
        content.pack(fill="both", expand=True, padx=24, pady=16)

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
            height=36,
            fg_color=Theme.SURFACE,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.TEXT_PRIMARY,
            placeholder_text_color=Theme.TEXT_MUTED
        )
        self.name_entry.pack(fill="x", pady=(0, 12))
        self.name_entry.focus()

        # Notes / Memo Field
        ctk.CTkLabel(
            content,
            text="NOTES / REMINDER (OPTIONAL)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        self.notes_entry = ctk.CTkEntry(
            content,
            placeholder_text="e.g. Clash team, duo partner, ranked decay reminder...",
            height=36,
            fg_color=Theme.SURFACE,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.TEXT_PRIMARY,
            placeholder_text_color=Theme.TEXT_MUTED
        )
        self.notes_entry.pack(fill="x", pady=(0, 12))

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
            height=34,
            fg_color=Theme.SURFACE,
            button_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.tag_menu.set("Main")
        self.tag_menu.pack(fill="x", pady=(0, 12))

        # Color Accent Choice
        ctk.CTkLabel(
            content,
            text="CARD COLOR ACCENT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 6))

        color_frame = ctk.CTkFrame(content, fg_color="transparent")
        color_frame.pack(fill="x", pady=(0, 16))

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
        btn_frame.pack(fill="x", padx=24, pady=(0, 18))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_SECONDARY,
            height=38,
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
            height=38,
            command=self._handle_save
        )
        save_btn.pack(side="right", expand=True, fill="x", padx=(8, 0))

    def _handle_save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Name Required", "Please enter a name for this account profile.", parent=self)
            return

        tag = self.tag_menu.get()
        color = self.selected_color.get()
        notes = self.notes_entry.get().strip()
        self.destroy()
        self.on_save(name, tag, color, "riot_client", notes)


class EditAccountModal(ctk.CTkToplevel):
    def __init__(self, parent, account: AccountProfile, on_save: Callable[[AccountProfile], None]):
        super().__init__(parent)
        self.account = account
        self.on_save = on_save
        self.title("Edit Account Profile")
        self.geometry("480x510")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_DARK)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 480) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 510) // 2
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
        content.pack(fill="both", expand=True, padx=24, pady=16)

        # Account Name
        ctk.CTkLabel(
            content,
            text="ACCOUNT NAME / LABEL",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        self.name_entry = ctk.CTkEntry(
            content,
            height=36,
            fg_color=Theme.SURFACE,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.name_entry.insert(0, self.account.name)
        self.name_entry.pack(fill="x", pady=(0, 12))
        self.name_entry.focus()

        # Notes / Memo Field
        ctk.CTkLabel(
            content,
            text="NOTES / REMINDER (OPTIONAL)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        self.notes_entry = ctk.CTkEntry(
            content,
            placeholder_text="e.g. Clash team, duo partner, ranked decay reminder...",
            height=36,
            fg_color=Theme.SURFACE,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.TEXT_PRIMARY,
            placeholder_text_color=Theme.TEXT_MUTED
        )
        if getattr(self.account, "notes", None):
            self.notes_entry.insert(0, self.account.notes)
        self.notes_entry.pack(fill="x", pady=(0, 12))

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
            height=34,
            fg_color=Theme.SURFACE,
            button_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.tag_menu.set(self.account.tag if self.account.tag in Theme.TAG_OPTIONS else "Main")
        self.tag_menu.pack(fill="x", pady=(0, 12))

        # Color Accent
        ctk.CTkLabel(
            content,
            text="CARD COLOR ACCENT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 6))

        color_frame = ctk.CTkFrame(content, fg_color="transparent")
        color_frame.pack(fill="x", pady=(0, 16))

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
        btn_frame.pack(fill="x", padx=24, pady=(0, 18))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_SECONDARY,
            height=38,
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
            height=38,
            command=self._handle_save
        )
        save_btn.pack(side="right", expand=True, fill="x", padx=(8, 0))

    def _handle_save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Name Required", "Please enter an account name.", parent=self)
            return

        tag = self.tag_menu.get()
        self.account.name = name
        self.account.tag = tag
        self.account.color = self.selected_color.get()
        self.account.notes = self.notes_entry.get().strip()
        self.account.preferred_game = "riot_client"

        self.destroy()
        self.on_save(self.account)


class SettingsModal(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        settings: AppSettings,
        on_save: Callable[[AppSettings], None],
        on_export: Optional[Callable[[], None]] = None,
        on_import: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.settings = settings
        self.on_save = on_save
        self.on_export = on_export
        self.on_import = on_import
        self.title("Application Settings")
        self.geometry("540x540")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_DARK)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 540) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 540) // 2
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
            text="Configure Riot Client executable, startup, and backups.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", padx=24, pady=(0, 16))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=16)

        # Riot Client Path
        ctk.CTkLabel(
            content,
            text="RIOT CLIENT PATH (RiotClientServices.exe)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        path_row = ctk.CTkFrame(content, fg_color="transparent")
        path_row.pack(fill="x", pady=(0, 12))

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

        # Launch & System Settings
        ctk.CTkLabel(
            content,
            text="BEHAVIOR & INTEGRATION",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(4, 6))

        self.auto_launch_var = ctk.BooleanVar(value=self.settings.auto_launch)
        self.auto_launch_cb = ctk.CTkCheckBox(
            content,
            text="Automatically launch Riot Client immediately after switching",
            variable=self.auto_launch_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_PRIMARY,
            fg_color=Theme.ACCENT_CYAN,
            hover_color=Theme.ACCENT_CYAN_HOVER
        )
        self.auto_launch_cb.pack(anchor="w", pady=(2, 6))

        self.close_after_launch_var = ctk.BooleanVar(value=getattr(self.settings, "close_after_launch", False))
        self.close_after_launch_cb = ctk.CTkCheckBox(
            content,
            text="Minimize Riot Link to system tray after launching Riot Client",
            variable=self.close_after_launch_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_PRIMARY,
            fg_color=Theme.ACCENT_CYAN,
            hover_color=Theme.ACCENT_CYAN_HOVER
        )
        self.close_after_launch_cb.pack(anchor="w", pady=(2, 6))

        self.start_with_windows_var = ctk.BooleanVar(value=getattr(self.settings, "start_with_windows", False))
        self.start_with_windows_cb = ctk.CTkCheckBox(
            content,
            text="Start Riot Link automatically on Windows startup",
            variable=self.start_with_windows_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_PRIMARY,
            fg_color=Theme.ACCENT_CYAN,
            hover_color=Theme.ACCENT_CYAN_HOVER
        )
        self.start_with_windows_cb.pack(anchor="w", pady=(2, 12))

        # Backup & Restore Section
        backup_card = ctk.CTkFrame(content, fg_color=Theme.SURFACE, corner_radius=8, border_width=1, border_color=Theme.CARD_BORDER)
        backup_card.pack(fill="x", pady=(4, 8), padx=0)

        backup_header = ctk.CTkFrame(backup_card, fg_color="transparent")
        backup_header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            backup_header,
            text="PORTABLE BACKUP & RESTORE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            backup_header,
            text="Export or restore your saved account profiles and settings as a portable .zip archive.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor="w")

        backup_btn_row = ctk.CTkFrame(backup_card, fg_color="transparent")
        backup_btn_row.pack(fill="x", padx=12, pady=(6, 10))

        export_btn = ctk.CTkButton(
            backup_btn_row,
            text="📦 Export Accounts (.zip)",
            height=32,
            fg_color=Theme.CARD_BG,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._handle_export_click
        )
        export_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        import_btn = ctk.CTkButton(
            backup_btn_row,
            text="📥 Import Accounts (.zip)",
            height=32,
            fg_color=Theme.CARD_BG,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._handle_import_click
        )
        import_btn.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 18))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_SECONDARY,
            height=38,
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
            height=38,
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

    def _handle_export_click(self):
        if self.on_export:
            self.on_export()

    def _handle_import_click(self):
        if self.on_import:
            self.on_import()

    def _handle_save(self):
        path_val = self.path_entry.get().strip()
        self.settings.riot_client_path = path_val or None
        self.settings.auto_launch = self.auto_launch_var.get()
        self.settings.close_after_launch = self.close_after_launch_var.get()
        self.settings.start_with_windows = self.start_with_windows_var.get()
        self.destroy()
        self.on_save(self.settings)


class RiotClientSetupModal(ctk.CTkToplevel):
    """
    First-run setup modal shown when Riot Client is not found automatically
    in the default installation paths.
    """
    def __init__(self, parent, on_saved: Callable[[str], None]):
        super().__init__(parent)
        self.on_saved = on_saved
        self.title("Riot Client Setup Required")
        self.geometry("540x480")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_DARK)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 540) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 480) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self._build_ui()

    def _build_ui(self):
        # Header banner
        header = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            header,
            text="RIOT CLIENT NOT DETECTED",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=Theme.WARNING
        ).pack(anchor="w", padx=24, pady=(16, 4))

        ctk.CTkLabel(
            header,
            text="Riot Link needs to know where RiotClientServices.exe is located on your PC.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", padx=24, pady=(0, 16))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=(16, 12))

        # Help / Instructions Card
        help_card = ctk.CTkFrame(content, fg_color=Theme.SURFACE, corner_radius=8, border_width=1, border_color=Theme.CARD_BORDER)
        help_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            help_card,
            text="💡 Quick Guide to Locate Your Riot Client",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=Theme.ACCENT_CYAN
        ).pack(anchor="w", padx=14, pady=(10, 4))

        help_text = (
            "1. Common Default Folders:\n"
            "   • C:\\Riot Games\\Riot Client\\RiotClientServices.exe\n"
            "   • D:\\Riot Games\\Riot Client\\RiotClientServices.exe\n\n"
            "2. Shortcut Trick:\n"
            "   Right-click your Riot Client desktop or start menu icon, "
            "select 'Open file location', and select RiotClientServices.exe."
        )
        ctk.CTkLabel(
            help_card,
            text=help_text,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Theme.TEXT_SECONDARY,
            justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 12))

        # Path input
        ctk.CTkLabel(
            content,
            text="LOCATE RIOTCLIENTSERVICES.EXE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 4))

        path_row = ctk.CTkFrame(content, fg_color="transparent")
        path_row.pack(fill="x", pady=(0, 8))

        self.path_entry = ctk.CTkEntry(
            path_row,
            height=36,
            placeholder_text="Click Browse to select RiotClientServices.exe...",
            fg_color=Theme.SURFACE,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.TEXT_PRIMARY
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ctk.CTkButton(
            path_row,
            text="Browse...",
            width=84,
            height=36,
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            command=self._browse_path
        )
        browse_btn.pack(side="right")

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 18))

        skip_btn = ctk.CTkButton(
            btn_frame,
            text="I'll Set It Later",
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_SECONDARY,
            height=40,
            command=self.destroy
        )
        skip_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save Riot Client Path",
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
            title="Locate RiotClientServices.exe",
            filetypes=[
                ("Riot Client Services", "RiotClientServices.exe"),
                ("Executable Files", "*.exe"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, file_path)

    def _handle_save(self):
        val = self.path_entry.get().strip()
        if not val:
            messagebox.showwarning(
                "Path Required",
                "Please click Browse to select your RiotClientServices.exe location.",
                parent=self
            )
            return

        from pathlib import Path
        path_obj = Path(val)
        if not path_obj.is_file():
            messagebox.showerror(
                "File Not Found",
                f"The selected file does not exist:\n{val}",
                parent=self
            )
            return

        if path_obj.name.lower() != "riotclientservices.exe":
            confirm = messagebox.askyesno(
                "Different File Selected",
                f"You selected '{path_obj.name}' instead of 'RiotClientServices.exe'.\n\n"
                "Are you sure this is your main Riot Client executable?",
                parent=self
            )
            if not confirm:
                return

        self.on_saved(str(path_obj))
        self.destroy()


class WaitForRiotCloseModal(ctk.CTkToplevel):
    """
    Shown when switching accounts while Riot Client is still running.
    Guides the user to cleanly close Riot Client from their Windows taskbar
    or system tray. Automatically proceeds as soon as Riot Client closes!
    Also provides a safe 'Close Launcher' button (only terminates RiotClientServices.exe, never games).
    """
    def __init__(self, parent, on_proceed: Callable[[], None], on_cancel: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.parent = parent
        self.on_proceed = on_proceed
        self.on_cancel = on_cancel
        self.title("Please Close Riot Client")
        self.geometry("500x360")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_DARK)
        self.transient(parent)
        self.grab_set()

        self._check_timer = None
        self._is_closing = False

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 500) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 360) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)
        self._build_ui()
        self._check_loop()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            header,
            text="PLEASE EXIT RIOT CLIENT",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=Theme.ACCENT_CYAN
        ).pack(anchor="w", padx=24, pady=(16, 4))

        ctk.CTkLabel(
            header,
            text="Riot Client must be closed to swap session files cleanly.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", padx=24, pady=(0, 16))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=16)

        # Instructions card
        card = ctk.CTkFrame(content, fg_color=Theme.SURFACE, corner_radius=8, border_width=1, border_color=Theme.CARD_BORDER)
        card.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            card,
            text="💡 Clean Exit from Taskbar / Tray (Recommended)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=14, pady=(10, 4))

        guide = (
            "Right-click the Riot icon in your Windows Taskbar or System Tray\n"
            "(near your clock) and click 'Exit'.\n\n"
            "Riot Link will auto-detect the exit and proceed immediately!"
        )
        ctk.CTkLabel(
            card,
            text=guide,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Theme.TEXT_SECONDARY,
            justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 12))

        # Status label
        self.status_lbl = ctk.CTkLabel(
            content,
            text="⏳ Waiting for Riot Client to close...",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#f59e0b"
        )
        self.status_lbl.pack(pady=(0, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 18))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_SECONDARY,
            height=38,
            command=self._handle_cancel
        )
        cancel_btn.pack(side="left", padx=(0, 8))

        self.kill_btn = ctk.CTkButton(
            btn_frame,
            text="Close Launcher Now",
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.ACCENT_RED,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            height=38,
            command=self._handle_close_launcher_now
        )
        self.kill_btn.pack(side="right", expand=True, fill="x")

    def _check_loop(self):
        if self._is_closing:
            return
        from ...process_manager import ProcessManager
        if not ProcessManager.is_riot_running():
            self._on_client_closed()
            return
        self._check_timer = self.after(400, self._check_loop)

    def _handle_close_launcher_now(self):
        self.status_lbl.configure(text="⏳ Closing Riot Client launcher UI...", text_color="#f59e0b")
        from ...process_manager import ProcessManager
        ProcessManager.close_riot_client_launcher(timeout=3.0)

    def _on_client_closed(self):
        self._is_closing = True
        if self._check_timer:
            self.after_cancel(self._check_timer)
        self.destroy()
        if self.on_proceed:
            self.on_proceed()

    def _handle_cancel(self):
        self._is_closing = True
        if self._check_timer:
            self.after_cancel(self._check_timer)
        self.destroy()
        if self.on_cancel:
            self.on_cancel()


class GuideModal(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("User Guide & FAQ — Everything You Should Know")
        self.geometry("580x640")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_DARK)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 580) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 640) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self._build_ui()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(fill="x", padx=24, pady=(16, 4))

        ctk.CTkLabel(
            title_row,
            text="HELP, GUIDE & FAQ",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(side="left")

        badge = ctk.CTkLabel(
            title_row,
            text=" ALL-IN-ONE ",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#064e3b",
            text_color="#34d399",
            corner_radius=4,
            height=20
        )
        badge.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(
            header,
            text="Everything you should know about adding accounts, switching, and safety.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", padx=24, pady=(0, 16))

        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=14)

        sections = [
            (
                "🔑  How to Add Your First Account",
                "1. Open the official Riot Client.\n"
                "2. Type your username and password.\n"
                "3. IMPORTANT: Make sure 'Stay signed in' is CHECKED!\n"
                "4. Complete 2FA (if prompted) until you see the Riot Client home screen.\n"
                "5. Open this app and click '+ SAVE CURRENT ACCOUNT' at the top!"
            ),
            (
                "➕  How to Add More Accounts (Account #2, #3...)",
                "⚠️ DO NOT click 'Sign Out' in Riot Client!\n\n"
                "1. In this app, click '🔑 LOG IN ANOTHER ACCOUNT'.\n"
                "2. This safely closes Riot Client and opens a clean login screen without disconnecting your first account.\n"
                "3. Log into your next account (check 'Stay signed in').\n"
                "4. Once on the home screen, click '+ SAVE CURRENT ACCOUNT'!"
            ),
            (
                "⚡  1-Click Instant Switching",
                "• Click 'SWITCH ACCOUNT' on any account card to switch instantly.\n"
                "• Riot Link swaps your login session and opens the official Riot Client already logged in!\n"
                "• From Riot Client, you simply click 'Play' on whatever game you want to play.\n"
                "• Zero game command injection or memory access."
            ),
            (
                "⚠️  Why You Should NEVER Click 'Sign Out' in Riot Client",
                "Clicking 'Sign Out' in Riot Client sends a request to Riot's auth servers to permanently revoke and destroy that session token.\n\n"
                "• Always switch accounts directly from this Switcher app instead of logging out.\n"
                "• If you want to log into an unsaved account, always use '🔑 LOG IN ANOTHER ACCOUNT'."
            ),
            (
                "🔄  What to Do If an Account Shows [LOGGED OUT]",
                "If Riot Client was signed out, the card displays ⚠️ LOGGED OUT with an amber border.\n\n"
                "To fix it in 15 seconds:\n"
                "1. Open Riot Client and sign into that account normally (check 'Stay signed in').\n"
                "2. Return to this app and click the highlighted 🔄 (Refresh) button on that account's card.\n"
                "3. Your session is instantly re-linked and ready for 1-click switching again!"
            ),
            (
                "🛡️  Does It Touch the Game or Riot Vanguard?",
                "No. This app NEVER touches game memory, never injects code, never modifies game files, never force-kills live game matches, and never interacts with Vanguard.\n\n"
                "• It only swaps Riot Client's official 'Stay signed in' files while Riot Client is closed, then starts the official Riot Client via Windows.\n"
                "• Live game processes are NEVER terminated by Riot Link."
            ),
            (
                "🔒  Security & 2FA (Two-Factor Authentication)",
                "• No Passwords Stored: This app NEVER asks for or stores your Riot password.\n"
                "• Local Storage Only: Session tokens are stored only on your PC in %APPDATA%. Treat that folder like a password — don't share it.\n"
                "• 2FA Persistence: You only enter 2FA once when saving the account. Riot's servers remember your PC, so switching accounts skips 2FA prompts automatically!"
            ),
            (
                "🛠️  Account Card Controls",
                "• ✏️ Edit: Change account nickname, tag label, or avatar color.\n"
                "• 🔄 Refresh: Re-link or renew token when Riot asks for a login update.\n"
                "• 🗑️ Delete: Remove account profile from this app (this will NOT delete your real Riot account)."
            ),
        ]

        for step_title, step_desc in sections:
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
                wraplength=500
            ).pack(anchor="w", padx=14, pady=(0, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 18))

        got_it_btn = ctk.CTkButton(
            btn_frame,
            text="Got It, Close Guide",
            fg_color=Theme.ACCENT_CYAN,
            hover_color=Theme.ACCENT_CYAN_HOVER,
            text_color="#000000",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=40,
            command=self.destroy
        )
        got_it_btn.pack(fill="x")


class UpdateModal(ctk.CTkToplevel):
    """
    Update modal that displays release notes and seamlessly downloads
    and applies the new Riot Link executable in-place.
    """
    def __init__(self, parent, release_info: dict):
        super().__init__(parent)
        self.parent = parent
        self.release_info = release_info
        self.title("Riot Link Update Available")
        self.geometry("520x480")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_DARK)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 520) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 480) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self._build_ui()

    def _build_ui(self):
        # Header banner
        header = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            header,
            text="🎉 NEW UPDATE AVAILABLE",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=Theme.ACCENT_CYAN
        ).pack(anchor="w", padx=24, pady=(16, 4))

        ctk.CTkLabel(
            header,
            text=f"A new version of Riot Link ({self.release_info.get('tag', '')}) is ready to install!",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", padx=24, pady=(0, 16))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=16)

        # Version Pill Row
        ver_row = ctk.CTkFrame(content, fg_color=Theme.SURFACE, corner_radius=8, border_width=1, border_color=Theme.CARD_BORDER)
        ver_row.pack(fill="x", pady=(0, 12))

        ver_inner = ctk.CTkFrame(ver_row, fg_color="transparent")
        ver_inner.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(
            ver_inner,
            text=f"Current: v{Config.APP_VERSION}",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_MUTED
        ).pack(side="left")

        ctk.CTkLabel(
            ver_inner,
            text=" ➔ ",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=Theme.ACCENT_CYAN
        ).pack(side="left", padx=8)

        ctk.CTkLabel(
            ver_inner,
            text=f"Latest: {self.release_info.get('tag', '')}",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#10b981"
        ).pack(side="left")

        # Release Notes Title & Box
        ctk.CTkLabel(
            content,
            text="WHAT'S NEW IN THIS VERSION",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 6))

        self.notes_box = ctk.CTkTextbox(
            content,
            height=140,
            fg_color=Theme.SURFACE,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.notes_box.pack(fill="both", expand=True, pady=(0, 14))
        self.notes_box.insert("1.0", self.release_info.get("notes", "No release notes."))
        self.notes_box.configure(state="disabled")

        # Progress Section (Initially hidden)
        self.progress_frame = ctk.CTkFrame(content, fg_color="transparent")
        
        self.progress_lbl = ctk.CTkLabel(
            self.progress_frame,
            text="Preparing download...",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        self.progress_lbl.pack(anchor="w", pady=(0, 6))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            height=12,
            fg_color=Theme.SURFACE,
            progress_color=Theme.ACCENT_CYAN
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0.0)

        # Action Buttons Row
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=24, pady=(0, 20))

        self.later_btn = ctk.CTkButton(
            self.btn_frame,
            text="Remind Later",
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_SECONDARY,
            height=40,
            command=self.destroy
        )
        self.later_btn.pack(side="left", padx=(0, 8))

        self.github_btn = ctk.CTkButton(
            self.btn_frame,
            text="View Release",
            fg_color=Theme.SURFACE,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            height=40,
            command=self._open_github
        )
        self.github_btn.pack(side="left", padx=(0, 8))

        self.update_btn = ctk.CTkButton(
            self.btn_frame,
            text="⚡ Update Now",
            fg_color=Theme.ACCENT_CYAN,
            hover_color=Theme.ACCENT_CYAN_HOVER,
            text_color="#000000",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=40,
            command=self._start_update
        )
        self.update_btn.pack(side="right", expand=True, fill="x")

    def _open_github(self):
        url = self.release_info.get("html_url") or Config.GITHUB_RELEASES_URL
        webbrowser.open(url)

    def _start_update(self):
        download_url = self.release_info.get("download_url")
        if not download_url:
            # If no .exe asset is attached, direct to GitHub Releases
            messagebox.showinfo(
                "Manual Download Required",
                "No direct executable asset found for this release.\nOpening the release page on GitHub...",
                parent=self
            )
            self._open_github()
            self.destroy()
            return

        # Show progress bar and disable close
        self.btn_frame.pack_forget()
        self.progress_frame.pack(fill="x", pady=(0, 10))
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        threading.Thread(target=self._run_download, args=(download_url,), daemon=True).start()

    def _run_download(self, download_url: str):
        try:
            from ...updater import UpdateManager

            def on_progress(fraction: float, downloaded: int, total: int):
                mb_curr = downloaded / (1024 * 1024)
                mb_tot = total / (1024 * 1024)
                pct = int(fraction * 100)
                text = f"Downloading: {mb_curr:.1f} MB / {mb_tot:.1f} MB ({pct}%)"
                self.after(0, lambda: self._update_ui_progress(fraction, text))

            tmp_exe, target_exe = UpdateManager.download_and_verify_update(
                download_url,
                progress_callback=on_progress,
                checksums_url=self.release_info.get("checksums_url"),
                asset_name=self.release_info.get("asset_name"),
            )
            self._tmp_exe = tmp_exe
            self._target_exe = target_exe
            self.after(0, self._on_download_complete)
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: self._on_download_error(err_msg))

    def _update_ui_progress(self, frac: float, text: str):
        self.progress_bar.set(frac)
        self.progress_lbl.configure(text=text)

    def _on_download_complete(self):
        self.progress_bar.set(1.0)
        self.progress_lbl.configure(text="✅ Update verified! Applying and restarting...", text_color="#10b981")
        self.after(800, self._finish_restart)

    def _finish_restart(self):
        from ...updater import UpdateManager
        # Release single instance mutex and stop tray icon before replacing
        try:
            if hasattr(self.parent, "single_instance") and self.parent.single_instance:
                self.parent.single_instance.cleanup()
            if hasattr(self.parent, "tray_mgr") and self.parent.tray_mgr:
                self.parent.tray_mgr.stop()
            self.parent.destroy()
        except Exception:
            pass

        # Perform in-place rename and native restart (zero cmd prompt)
        UpdateManager.apply_update_and_restart(self._tmp_exe, self._target_exe)

    def _on_download_error(self, err_msg: str):
        messagebox.showerror(
            "Update Error",
            f"Failed to automatically update Riot Link:\n{err_msg}\n\nYou can download the latest release manually from GitHub.",
            parent=self
        )
        self._open_github()
        self.destroy()
