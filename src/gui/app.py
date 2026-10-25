"""
Main Application Window for Riot Account Switcher.
Responsive, modern gaming dashboard with custom icon and direct controls.
"""

from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image

from .theme import Theme
from .components.dialogs import AddAccountModal, EditAccountModal, SettingsModal, GuideModal
from .components.account_card import AccountCard
from ..session_manager import SessionManager
from ..process_manager import ProcessManager
from ..config import Config
from ..models import AccountProfile, AppSettings


class RiotAccountSwitcherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Riot Account Switcher & Launcher")
        self.geometry("820x680")
        self.minsize(580, 520)
        self.configure(fg_color=Theme.BG_DARK)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        # Load & Set Window Icon
        self._load_window_icon()

        # Initialize Managers
        self.session_mgr = SessionManager()

        # State
        self.search_query = ""
        self.active_account_id = None

        self._build_layout()
        self._refresh_ui()

        # Periodic status check (every 3 seconds)
        self.after(3000, self._periodic_status_check)

    def _load_window_icon(self):
        """Set window icon from assets if available."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        ico_path = base_dir / "assets" / "icon.ico"

        if ico_path.is_file():
            try:
                self.iconbitmap(default=str(ico_path))
            except Exception:
                pass

        self.logo_image = None
        logo_png = base_dir / "assets" / "logo_48.png"
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
            text="RIOT ACCOUNT SWITCHER",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        app_title.pack(anchor="w")

        app_subtitle = ctk.CTkLabel(
            title_col,
            text="Instant 1-Click Login • 2FA Persistent • 100% Anti-Cheat Safe",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Theme.TEXT_MUTED
        )
        app_subtitle.pack(anchor="w")

        # Top Right Controls (Guide & Settings)
        top_right_controls = ctk.CTkFrame(brand_row, fg_color="transparent")
        top_right_controls.pack(side="right")

        self.guide_btn = ctk.CTkButton(
            top_right_controls,
            text="📖 How to Add Accounts",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=Theme.CARD_BG,
            hover_color=Theme.SURFACE_HOVER,
            text_color=Theme.ACCENT_CYAN,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            height=32,
            corner_radius=6,
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
        # App Version Badge on the right (Clean native desktop style)
        version_frame = ctk.CTkFrame(footer_inner, fg_color="transparent")
        version_frame.pack(side="right")

        pulse_dot = ctk.CTkLabel(
            version_frame,
            text="●",
            font=ctk.CTkFont(size=9),
            text_color="#10b981"
        )
        pulse_dot.pack(side="left", padx=(0, 5))

        version_lbl = ctk.CTkLabel(
            version_frame,
            text="v1.2.0 • Ready",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Theme.TEXT_MUTED
        )
        version_lbl.pack(side="left")

    def _refresh_ui(self):
        """Re-render account cards and update status badges."""
        self.active_account_id = self.session_mgr.get_active_account_id()
        is_running = ProcessManager.is_riot_running()

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
            # Show compact drive:\...\RiotClientServices.exe
            compact_p = f"{p.drive}\\...\\{p.name}"
            self.footer_path_lbl.configure(text=f"Riot: {compact_p}")
        else:
            self.footer_path_lbl.configure(text="Riot Path: Not Found (Click ⚙)")

        # Clear existing cards
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

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
            is_active = (acc.id == self.active_account_id)
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
        try:
            self.session_mgr.switch_to_account(account_id, launch_product=product, auto_launch=True)
            self._refresh_ui()
        except Exception as e:
            messagebox.showerror("Switch Error", f"Failed to switch account:\n{e}", parent=self)

    def _handle_update_token(self, account_id: str):
        confirm = messagebox.askyesno(
            "Refresh Session Token",
            "This will overwrite this account profile with the session currently active in Riot Client.\n\n"
            "Use this if you recently renewed your password or 2FA.\n\nContinue?",
            parent=self
        )
        if confirm:
            try:
                self.session_mgr.update_account_session(account_id)
                self._refresh_ui()
                messagebox.showinfo("Success", "Account session token updated successfully!", parent=self)
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
            self.session_mgr.prepare_new_login()
            self._refresh_ui()

    def _handle_close_riot(self):
        closed = ProcessManager.close_all_riot_processes(timeout=4.0)
        self._refresh_ui()
        if closed:
            self.status_pill.configure(
                text=" ○ RIOT CLIENT CLOSED ",
                fg_color=Theme.SURFACE,
                text_color=Theme.TEXT_MUTED
            )

    def _handle_direct_launch(self, product: str):
        path_str = self.session_mgr.settings.riot_client_path or Config.find_riot_client_path()
        if not path_str:
            messagebox.showwarning("Riot Path Missing", "Please set Riot Client path in Settings.", parent=self)
            return
        from pathlib import Path
        ProcessManager.launch(Path(path_str), product=product)
        self._refresh_ui()

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
        """Check status periodically to keep the status indicator responsive."""
        is_running = ProcessManager.is_riot_running()
        active_id = self.session_mgr.get_active_account_id()
        if active_id != self.active_account_id:
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
