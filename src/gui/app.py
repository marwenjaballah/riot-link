"""
Main Application Window for Riot Account Switcher.
Responsive, modern gaming dashboard with custom icon and direct controls.
"""

import webbrowser
import threading
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image

from .theme import Theme
from .components.dialogs import (
    AddAccountModal,
    EditAccountModal,
    SettingsModal,
    GuideModal,
    RiotClientSetupModal,
    UpdateModal,
)
from .components.account_card import AccountCard
from ..session_manager import SessionManager
from ..process_manager import ProcessManager
from ..updater import UpdateManager
from ..tray import TrayIconManager
from ..config import Config
from ..models import AccountProfile, AppSettings


class RiotAccountSwitcherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title(f"{Config.APP_NAME} v{Config.APP_VERSION}")
        self.geometry("820x680")
        self.minsize(580, 520)
        self.configure(fg_color=Theme.BG_DARK)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        # Load & Set Window Icon
        self._load_window_icon()

        # Initialize Managers
        self.session_mgr = SessionManager()

        # System Tray Manager (runs detached in background)
        self.tray_mgr = TrayIconManager(
            on_show=self._show_window_from_tray,
            on_exit=self._exit_app_from_tray,
            on_check_updates=self._handle_manual_check_updates,
            get_accounts=self.session_mgr.get_accounts,
            on_switch_account=self._switch_from_tray,
        )
        self.tray_mgr.start()

        # Minimize to System Tray when close button ('X') is clicked
        self.protocol("WM_DELETE_WINDOW", self._on_close_to_tray)

        # State
        self.search_query = ""
        self.active_account_id = None
        self._available_update = None

        self._build_layout()
        self._refresh_ui()

        # Verify Riot Client path on first run / startup
        self.after(350, self._check_initial_riot_path)

        # Check for updates in background (non-blocking)
        self.after(2500, self._check_updates_background)

        # Periodic status check (every 3 seconds)
        self.after(3000, self._periodic_status_check)

    def _load_window_icon(self):
        """Set window icon from assets if available."""
        assets_dir = Config.get_assets_dir()
        ico_path = assets_dir / "icon.ico"

        if ico_path.is_file():
            try:
                self.iconbitmap(default=str(ico_path))
            except Exception:
                pass

        self.logo_image = None
        logo_png = assets_dir / "logo_48.png"
        if logo_png.is_file():
            try:
                pil_img = Image.open(logo_png)
                self.logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(38, 38))
            except Exception:
                pass

    def _build_layout(self):
        # 1. Top Navbar / Header (2-tier responsive layout so buttons never clip!)
        self.nav_frame = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=0)
        self.nav_frame.pack(fill="x", side="top")

        nav_inner = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        nav_inner.pack(fill="x", padx=18, pady=(12, 12))

        # Top Row of Navbar: Brand / Title on Left, Settings on Right
        brand_row = ctk.CTkFrame(nav_inner, fg_color="transparent")
        brand_row.pack(fill="x", pady=(0, 10))

        brand_left = ctk.CTkFrame(brand_row, fg_color="transparent")
        brand_left.pack(side="left")

        if self.logo_image:
            logo_label = ctk.CTkLabel(brand_left, text="", image=self.logo_image)
            logo_label.pack(side="left", padx=(0, 12))

        title_col = ctk.CTkFrame(brand_left, fg_color="transparent")
        title_col.pack(side="left")

        app_title = ctk.CTkLabel(
            title_col,
            text=Config.APP_NAME.upper(),
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        app_title.pack(anchor="w")

        app_subtitle = ctk.CTkLabel(
            title_col,
            text=Config.APP_TAGLINE,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Theme.TEXT_MUTED
        )
        app_subtitle.pack(anchor="w")

        # Top Right Controls (Guide & Settings)
        top_right_controls = ctk.CTkFrame(brand_row, fg_color="transparent")
        top_right_controls.pack(side="right")

        self.guide_btn = ctk.CTkButton(
            top_right_controls,
            text="?",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=Theme.CARD_BG,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.ACCENT_CYAN,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            width=32,
            height=32,
            corner_radius=16,
            command=self._open_guide_modal
        )
        self.guide_btn.pack(side="left", padx=(0, 8))

        self.settings_btn = ctk.CTkButton(
            top_right_controls,
            text="⚙ Settings",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=Theme.CARD_BG,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_SECONDARY,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            height=32,
            width=86,
            corner_radius=6,
            command=self._open_settings_modal
        )
        self.settings_btn.pack(side="left")

        # Action Toolbar Row (Always visible and responsive)
        self.action_bar = ctk.CTkFrame(nav_inner, fg_color="transparent")
        self.action_bar.pack(fill="x")

        self.add_btn = ctk.CTkButton(
            self.action_bar,
            text="+ SAVE CURRENT ACCOUNT",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=Theme.ACCENT_RED,
            hover_color=Theme.ACCENT_RED_HOVER,
            height=36,
            corner_radius=6,
            command=self._open_add_modal
        )
        self.add_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.new_login_btn = ctk.CTkButton(
            self.action_bar,
            text="🔑 LOG IN ANOTHER ACCOUNT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=Theme.CARD_BG,
            hover_color=Theme.SURFACE_HOVER,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.ACCENT_CYAN,
            height=36,
            corner_radius=6,
            command=self._handle_prepare_new_login
        )
        self.new_login_btn.pack(side="left", expand=True, fill="x", padx=6)

        self.kill_btn = ctk.CTkButton(
            self.action_bar,
            text="CLOSE RIOT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=Theme.CARD_BG,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.DANGER,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            height=36,
            width=100,
            corner_radius=6,
            command=self._handle_close_riot
        )
        self.kill_btn.pack(side="left", padx=(6, 0))

        # 2. Sub-Header: Status Pill, Active Account Info, and Search
        sub_bar = ctk.CTkFrame(self, fg_color="transparent")
        sub_bar.pack(fill="x", padx=18, pady=(14, 10))

        # Left Status Pill
        self.status_pill = ctk.CTkLabel(
            sub_bar,
            text=" Checking Riot Client... ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=Theme.SURFACE,
            text_color=Theme.TEXT_SECONDARY,
            corner_radius=6,
            height=28
        )
        self.status_pill.pack(side="left", padx=(0, 10))

        # Active account indicator label
        self.active_acc_lbl = ctk.CTkLabel(
            sub_bar,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Theme.TEXT_MUTED
        )
        self.active_acc_lbl.pack(side="left")

        # Search Bar on Right
        self.search_entry = ctk.CTkEntry(
            sub_bar,
            placeholder_text="Search accounts or tags...",
            width=200,
            height=32,
            fg_color=Theme.SURFACE,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.TEXT_PRIMARY,
            placeholder_text_color=Theme.TEXT_MUTED
        )
        self.search_entry.pack(side="right")
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)

        # 3. Main Content: Scrollable Accounts List
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        # 4. Bottom Footer Toolbar (Collision-Free & Compact)
        footer = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=0, height=44)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        footer_inner = ctk.CTkFrame(footer, fg_color="transparent")
        footer_inner.pack(fill="both", expand=True, padx=18)

        self.footer_path_lbl = ctk.CTkLabel(
            footer_inner,
            text="Riot Path: Detecting...",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Theme.TEXT_MUTED
        )
        self.footer_path_lbl.pack(side="left")

        # Developer Signature (Center, clickable GitHub link)
        self.signature_btn = ctk.CTkButton(
            footer_inner,
            text=f"Developed with ❤️ by {Config.AUTHOR_NAME}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="transparent",
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.TEXT_SECONDARY,
            height=28,
            corner_radius=6,
            command=lambda: webbrowser.open(Config.AUTHOR_GITHUB)
        )
        self.signature_btn.pack(side="left", expand=True)

        # App Version & Update Badge on the right (Clickable)
        self.version_btn = ctk.CTkButton(
            footer_inner,
            text=f"● v{Config.APP_VERSION}",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="transparent",
            hover_color=Theme.SURFACE_HOVER,
            text_color="#10b981",
            height=28,
            corner_radius=6,
            command=self._handle_manual_check_updates
        )
        self.version_btn.pack(side="right")

    def _refresh_ui(self):
        """Re-render account cards and update status badges."""
        self.active_account_id = self.session_mgr.get_active_account_id()
        has_session = self.session_mgr.has_active_riot_session()
        self._last_has_session = has_session
        is_running = ProcessManager.is_riot_running()

        # Update Save Button: Only active when an unsaved account is currently logged in!
        if not has_session:
            self.add_btn.configure(
                state="disabled",
                text="+ SAVE CURRENT ACCOUNT",
                fg_color=Theme.CARD_BG,
                text_color=Theme.TEXT_MUTED
            )
        elif self.active_account_id is not None:
            self.add_btn.configure(
                state="disabled",
                text="✓ CURRENT ACCOUNT SAVED",
                fg_color=Theme.CARD_BG,
                text_color=Theme.TEXT_MUTED
            )
        else:
            self.add_btn.configure(
                state="normal",
                text="+ SAVE CURRENT ACCOUNT",
                fg_color=Theme.ACCENT_RED,
                hover_color=Theme.ACCENT_RED_HOVER,
                text_color="#ffffff"
            )

        # Update Status Pill
        if is_running:
            self.status_pill.configure(
                text=" ● RIOT CLIENT RUNNING ",
                fg_color="#064e3b",
                text_color="#34d399"
            )
        else:
            self.status_pill.configure(
                text=" ○ RIOT CLIENT IDLE ",
                fg_color=Theme.SURFACE,
                text_color=Theme.TEXT_MUTED
            )

        # Update Active Account Hint
        accounts = self.session_mgr.get_accounts()
        active_acc = next((a for a in accounts if a.id == self.active_account_id), None)
        if active_acc:
            display_name = active_acc.username_hint or active_acc.name
            self.active_acc_lbl.configure(text=f"Active: {display_name}")
        else:
            self.active_acc_lbl.configure(text="")

        # Update Footer Path (Display compact path to prevent collision)
        detected_path = self.session_mgr.settings.riot_client_path or Config.find_riot_client_path()
        if detected_path:
            p = Path(detected_path)
            compact_p = f"{p.drive}\\...\\{p.name}"
            self.footer_path_lbl.configure(text=f"Riot: {compact_p}")
        else:
            self.footer_path_lbl.configure(text="Riot Path: Not Found (Click ⚙)")

        # Clear existing cards and banners
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # If any accounts require re-auth, show alert banner at the top of the list
        reauth_accounts = [a for a in accounts if a.needs_reauth]
        if reauth_accounts:
            names = ", ".join(f"'{a.name}'" for a in reauth_accounts)
            banner = ctk.CTkFrame(
                self.scroll_frame,
                fg_color="#451a03",
                corner_radius=8,
                border_width=1,
                border_color="#b45309"
            )
            banner.pack(fill="x", pady=(0, 8))

            ctk.CTkLabel(
                banner,
                text=f"⚠️ {names} was logged out in Riot Client. Sign in to Riot Client (check 'Stay signed in') and click 🔄 on the card to re-link.",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color="#fbbf24",
                wraplength=700,
                justify="left"
            ).pack(side="left", padx=14, pady=10)

        # Filter by search
        query = self.search_query.lower()
        if query:
            accounts = [
                acc for acc in accounts
                if query in acc.name.lower() or query in acc.tag.lower() or query in (acc.username_hint or "").lower()
            ]

        if not accounts:
            self._render_empty_state()
            return

        for acc in accounts:
            is_active = (acc.id == self.active_account_id and not acc.needs_reauth)
            card = AccountCard(
                self.scroll_frame,
                account=acc,
                is_active=is_active,
                on_switch=self._handle_switch,
                on_edit=self._open_edit_modal,
                on_update_token=self._handle_update_token,
                on_delete=self._handle_delete
            )
            card.pack(fill="x", pady=5)

        if hasattr(self, "tray_mgr") and self.tray_mgr:
            self.tray_mgr.update_menu()

    def _render_empty_state(self):
        empty_frame = ctk.CTkFrame(self.scroll_frame, fg_color=Theme.SURFACE, corner_radius=12)
        empty_frame.pack(fill="both", expand=True, padx=30, pady=30)

        ctk.CTkLabel(
            empty_frame,
            text="🎮",
            font=ctk.CTkFont(size=40)
        ).pack(pady=(28, 10))

        ctk.CTkLabel(
            empty_frame,
            text="No Riot Accounts Saved Yet",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(pady=(0, 6))

        guide_text = (
            "How to register your account:\n\n"
            "1. Open Riot Client and log in with 'Stay signed in' checked.\n"
            "2. Complete 2FA (if prompted).\n"
            "3. Click '+ SAVE CURRENT ACCOUNT' above!"
        )
        ctk.CTkLabel(
            empty_frame,
            text=guide_text,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Theme.TEXT_SECONDARY,
            justify="left"
        ).pack(pady=(0, 20))

        ctk.CTkButton(
            empty_frame,
            text="+ Save Current Logged-in Account",
            fg_color=Theme.ACCENT_RED,
            hover_color=Theme.ACCENT_RED_HOVER,
            height=38,
            command=self._open_add_modal
        ).pack(pady=(0, 28))

    def _open_add_modal(self):
        if not self.session_mgr.has_active_riot_session():
            messagebox.showwarning(
                "No Active Login Detected",
                "You are currently NOT logged in on Riot Client (or at the sign-in screen)!\n\n"
                "To save an account profile:\n"
                "1. Open the official Riot Client.\n"
                "2. Enter your username and password.\n"
                "3. IMPORTANT: Make sure 'Stay signed in' is CHECKED.\n"
                "4. Complete 2FA (if prompted) and wait until you are fully inside (seeing the Play button / friends list).\n"
                "5. Now click '+ SAVE CURRENT ACCOUNT' to capture this account!",
                parent=self
            )
            return

        active_id = self.session_mgr.get_active_account_id()
        if active_id is not None:
            accounts = self.session_mgr.get_accounts()
            active_acc = next((a for a in accounts if a.id == active_id), None)
            acc_name = active_acc.name if active_acc else "Current account"
            messagebox.showinfo(
                "Account Already Saved",
                f"The active account ({acc_name}) is already saved in your account list!\n\n"
                "If you want to add another account, click '🔑 LOG IN ANOTHER ACCOUNT'.",
                parent=self
            )
            return

        AddAccountModal(self, on_save=self._save_new_account)

    def _save_new_account(self, name: str, tag: str, color: str, preferred_game: str):
        try:
            self.session_mgr.save_current_account(
                name=name,
                tag=tag,
                color=color,
                preferred_game=preferred_game
            )
            self._refresh_ui()
            messagebox.showinfo("Saved!", f"Account profile '{name}' was saved successfully.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save account: {e}", parent=self)

    def _open_edit_modal(self, account: AccountProfile):
        EditAccountModal(self, account=account, on_save=self._save_edited_account)

    def _save_edited_account(self, updated_account: AccountProfile):
        try:
            self.session_mgr.update_account_metadata(updated_account)
            self._refresh_ui()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update account: {e}", parent=self)

    def _handle_switch(self, account_id: str, product: str):
        path_str = self.session_mgr.settings.riot_client_path
        if not path_str or not Path(path_str).is_file():
            detected = Config.find_riot_client_path()
            if detected and detected.is_file():
                self.session_mgr.settings.riot_client_path = str(detected)
                self.session_mgr.save_settings(self.session_mgr.settings)
            else:
                RiotClientSetupModal(self, on_saved=self._on_riot_path_configured)
                return

        account = self.session_mgr.get_account(account_id)
        if account and account.needs_reauth:
            confirm = messagebox.askyesno(
                "Account Was Logged Out",
                f"'{account.name}' was previously signed out in Riot Client, so Riot will show the sign-in screen.\n\n"
                "After you sign in (with 'Stay signed in' checked), click the 🔄 (Refresh) button on this card to restore 1-click switching.\n\n"
                "Launch Riot Client now to sign in?",
                parent=self
            )
            if not confirm:
                return

        try:
            self.session_mgr.switch_to_account(account_id, launch_product=product, auto_launch=True)
            self._refresh_ui()
        except Exception as e:
            messagebox.showerror("Switch Error", f"Failed to switch account:\n{e}", parent=self)

    def _handle_update_token(self, account_id: str):
        target_acc = self.session_mgr.get_account(account_id)
        acc_name = target_acc.name if target_acc else "this account"

        if not self.session_mgr.has_active_riot_session():
            messagebox.showwarning(
                "Riot Client Not Logged In",
                f"Cannot refresh or re-link '{acc_name}' because Riot Client is currently at the sign-in screen (no active session).\n\n"
                "To re-link:\n"
                "1. Open Riot Client and sign into this account (ensure 'Stay signed in' is checked).\n"
                "2. Complete 2FA (if prompted).\n"
                "3. Once you reach the home screen, click 🔄 (Refresh) again!",
                parent=self
            )
            return

        current_hint = self.session_mgr.extract_session_username_hint()
        confirm = messagebox.askyesno(
            "Re-Link Session Token",
            f"This will capture the session currently active in Riot Client and assign it to '{acc_name}'.\n\n"
            f"Active Session Detected: {current_hint or 'Riot Session'}\n\n"
            "This will clear the [LOGGED OUT] status and restore 1-click auto-login.\n\nContinue?",
            parent=self
        )
        if confirm:
            try:
                self.session_mgr.update_account_session(account_id)
                self.session_mgr.mark_account_reauth(account_id, False)
                self._refresh_ui()
                messagebox.showinfo(
                    "Re-Linked Successfully!",
                    f"Session for '{acc_name}' has been restored and updated successfully!\n"
                    "You can now switch to this account with 1 click.",
                    parent=self
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update session: {e}", parent=self)

    def _handle_delete(self, account_id: str):
        confirm = messagebox.askyesno(
            "Delete Profile",
            "Are you sure you want to delete this saved account profile?\n\n"
            "(This will not delete your actual Riot account, only the local switcher profile)",
            parent=self
        )
        if confirm:
            self.session_mgr.delete_account(account_id)
            self._refresh_ui()

    def _handle_prepare_new_login(self):
        confirm = messagebox.askyesno(
            "Log in to Another Account",
            "This will close Riot Client and launch a clean login screen so you can sign into another account.\n\n"
            "⚠️ IMPORTANT: Make sure your current account is already saved before proceeding!\n\n"
            "Open clean sign-in screen now?",
            parent=self
        )
        if confirm:
            self._is_preparing_new_login = True
            try:
                self.session_mgr.prepare_new_login()
                self.active_account_id = None
                self._refresh_ui()
            finally:
                self._is_preparing_new_login = False

    def _handle_close_riot(self):
        closed = ProcessManager.close_all_riot_processes(timeout=4.0)
        self._refresh_ui()
        if closed:
            self.status_pill.configure(
                text=" ○ RIOT CLIENT CLOSED ",
                fg_color=Theme.SURFACE,
                text_color=Theme.TEXT_MUTED
            )

    def _check_initial_riot_path(self):
        """
        Verify that RiotClientServices.exe exists in settings or default location.
        If not found, prompt the user with a setup dialog containing helpful instructions.
        """
        path_str = self.session_mgr.settings.riot_client_path
        if not path_str or not Path(path_str).is_file():
            detected = Config.find_riot_client_path()
            if detected and detected.is_file():
                self.session_mgr.settings.riot_client_path = str(detected)
                self.session_mgr.save_settings(self.session_mgr.settings)
                return

            # Open friendly setup modal with guidance
            RiotClientSetupModal(self, on_saved=self._on_riot_path_configured)

    def _on_riot_path_configured(self, new_path: str):
        self.session_mgr.settings.riot_client_path = new_path
        self.session_mgr.save_settings(self.session_mgr.settings)
        self._refresh_ui()

    def _handle_direct_launch(self, product: str):
        path_str = self.session_mgr.settings.riot_client_path
        if not path_str or not Path(path_str).is_file():
            detected = Config.find_riot_client_path()
            if detected and detected.is_file():
                path_str = str(detected)
                self.session_mgr.settings.riot_client_path = path_str
                self.session_mgr.save_settings(self.session_mgr.settings)
            else:
                RiotClientSetupModal(self, on_saved=self._on_riot_path_configured)
                return

        ProcessManager.launch(Path(path_str), product=product)
        self._refresh_ui()

    def _check_updates_background(self):
        """Check for updates silently in a background daemon thread."""
        def run_check():
            try:
                rel = UpdateManager.check_for_updates(timeout=4.0)
                if rel:
                    self.after(0, lambda: self._on_update_found(rel, auto=True))
            except Exception:
                pass

        threading.Thread(target=run_check, daemon=True).start()

    def _handle_manual_check_updates(self):
        """Manually check for updates when user clicks version or settings button."""
        self.version_btn.configure(text="Checking...", text_color=Theme.TEXT_MUTED)

        def run_check():
            try:
                rel = UpdateManager.check_for_updates(timeout=5.0)
                if rel:
                    self.after(0, lambda: self._on_update_found(rel, auto=False))
                else:
                    self.after(0, self._on_up_to_date)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Update Error", f"Could not check for updates:\n{e}", parent=self))
                self.after(0, lambda: self.version_btn.configure(text=f"● v{Config.APP_VERSION}", text_color="#10b981"))

        threading.Thread(target=run_check, daemon=True).start()

    def _on_update_found(self, release_info: dict, auto: bool = False):
        self._available_update = release_info
        tag = release_info.get("tag", "new")
        self.version_btn.configure(
            text=f"⚡ Update {tag} Available",
            text_color="#f59e0b"
        )
        UpdateModal(self, release_info=release_info)

    def _on_up_to_date(self):
        self.version_btn.configure(text=f"● v{Config.APP_VERSION}", text_color="#10b981")
        messagebox.showinfo(
            "Up to Date",
            f"You are running the latest version of Riot Link (v{Config.APP_VERSION})!\n\nNo updates are needed.",
            parent=self
        )

    def _open_guide_modal(self):
        GuideModal(self)

    def _open_settings_modal(self):
        SettingsModal(self, settings=self.session_mgr.settings, on_save=self._save_settings)

    def _save_settings(self, new_settings: AppSettings):
        self.session_mgr.save_settings(new_settings)
        self._refresh_ui()

    def _on_search_changed(self, event=None):
        self.search_query = self.search_entry.get().strip()
        self._refresh_ui()

    def _periodic_status_check(self):
        """Check status periodically to keep the status indicator and save button responsive."""
        is_running = ProcessManager.is_riot_running()
        active_id = self.session_mgr.get_active_account_id()
        has_session = self.session_mgr.has_active_riot_session()
        last_has_session = getattr(self, "_last_has_session", None)
        is_preparing_new_login = getattr(self, "_is_preparing_new_login", False)

        # Check for logout: User was on an active account, but now has_session is False (and it wasn't an intentional clean login preparation)
        if self.active_account_id and not has_session and not is_preparing_new_login:
            logged_out_id = self.active_account_id
            logged_out_acc = self.session_mgr.get_account(logged_out_id)
            self.active_account_id = None
            if logged_out_acc:
                self.session_mgr.mark_account_reauth(logged_out_id, True)
                self._refresh_ui()
                messagebox.showwarning(
                    "Session Logged Out in Riot Client",
                    f"Notice: You logged out of '{logged_out_acc.name}' in Riot Client.\n\n"
                    "⚠️ When you click 'Sign Out' in Riot Client, Riot permanently invalidates your saved login session on their authentication servers.\n\n"
                    f"'{logged_out_acc.name}' is now marked as [⚠️ LOGGED OUT].\n\n"
                    "How to reconnect this account:\n"
                    "1. Open Riot Client and sign into your account (make sure 'Stay signed in' is CHECKED).\n"
                    f"2. Return to this app and click the highlighted 🔄 (Refresh) button on '{logged_out_acc.name}' to save your new session!\n\n"
                    "💡 Tip: Never click 'Sign Out' in Riot Client. Always switch accounts directly inside this app!",
                    parent=self
                )
                self.after(3000, self._periodic_status_check)
                return

        if active_id != self.active_account_id or has_session != last_has_session:
            self._refresh_ui()
        else:
            if is_running:
                self.status_pill.configure(
                    text=" ● RIOT CLIENT RUNNING ",
                    fg_color="#064e3b",
                    text_color="#34d399"
                )
            else:
                self.status_pill.configure(
                    text=" ○ RIOT CLIENT IDLE ",
                    fg_color=Theme.SURFACE,
                    text_color=Theme.TEXT_MUTED
                )

        self.after(3000, self._periodic_status_check)

    # -------------------------------------------------------------------------
    # System Tray Handlers
    # -------------------------------------------------------------------------
    def _on_close_to_tray(self):
        """Minimize window to system tray when 'X' is clicked."""
        self.withdraw()
        if not getattr(self, "_has_shown_tray_tip", False):
            self._has_shown_tray_tip = True
            if self.tray_mgr:
                self.tray_mgr.notify(
                    "Riot Link Minimized",
                    "Riot Link is still running in the system tray.\nRight-click the icon to reopen, switch accounts, or exit."
                )

    def _show_window_from_tray(self):
        """Restore window from tray to foreground."""
        self.after(0, self._restore_window)

    def _restore_window(self):
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def _switch_from_tray(self, account_id: str):
        """Handle 1-click account switch initiated from the tray context menu."""
        self.after(0, lambda: self._handle_switch(account_id, product="riot_client"))

    def _exit_app_from_tray(self):
        """Exit the application cleanly from tray context menu."""
        self.after(0, self._destroy_and_exit)

    def _destroy_and_exit(self):
        if hasattr(self, "tray_mgr") and self.tray_mgr:
            self.tray_mgr.stop()
        self.destroy()
        import sys
        sys.exit(0)
