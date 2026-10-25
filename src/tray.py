"""
System tray manager for Riot Link using pystray.
Allows keeping Riot Link running in the system tray when the window is closed,
with a right-click context menu to reopen, switch accounts, check for updates, or exit.
"""

import sys
from typing import Callable, Optional
from PIL import Image
import pystray
from pystray import MenuItem as item, Menu

from .config import Config


class TrayIconManager:
    def __init__(
        self,
        on_show: Callable[[], None],
        on_exit: Callable[[], None],
        on_check_updates: Optional[Callable[[], None]] = None,
        get_accounts: Optional[Callable[[], list]] = None,
        on_switch_account: Optional[Callable[[str], None]] = None,
    ):
        self.on_show = on_show
        self.on_exit = on_exit
        self.on_check_updates = on_check_updates
        self.get_accounts = get_accounts
        self.on_switch_account = on_switch_account
        self.icon: Optional[pystray.Icon] = None
        self._init_tray()

    def _get_icon_image(self) -> Image.Image:
        assets_dir = Config.get_assets_dir()
        logo_png = assets_dir / "logo_48.png"
        if logo_png.is_file():
            try:
                return Image.open(logo_png)
            except Exception:
                pass
        ico_path = assets_dir / "icon.ico"
        if ico_path.is_file():
            try:
                return Image.open(ico_path)
            except Exception:
                pass
        return Image.new("RGB", (32, 32), color="#ff4655")

    def _build_menu(self) -> Menu:
        menu_items = [
            item("Open Riot Link", self._on_show_clicked, default=True),
        ]

        # Accounts quick-switch submenu
        if self.get_accounts and self.on_switch_account:
            try:
                accounts = self.get_accounts()
                if accounts:
                    account_items = []
                    for acc in accounts:
                        acc_id = acc.id
                        acc_label = f"{acc.name} ({acc.tag})" if acc.tag else acc.name

                        def make_handler(target_id=acc_id):
                            return lambda icon, itm: self.on_switch_account(target_id)

                        account_items.append(item(acc_label, make_handler()))
                    menu_items.append(item("Switch Account", Menu(*account_items)))
            except Exception:
                pass

        if self.on_check_updates:
            menu_items.append(item("Check for Updates", lambda icon, itm: self.on_check_updates()))

        menu_items.append(Menu.SEPARATOR)
        menu_items.append(item("Exit Riot Link", self._on_exit_clicked))

        return Menu(*menu_items)

    def _on_show_clicked(self, icon=None, item=None):
        if self.on_show:
            self.on_show()

    def _on_exit_clicked(self, icon=None, item=None):
        self.stop()
        if self.on_exit:
            self.on_exit()

    def update_menu(self):
        """Refresh dynamic menu items when accounts change."""
        if self.icon:
            try:
                self.icon.menu = self._build_menu()
            except Exception:
                pass

    def start(self):
        """Start the tray icon asynchronously without blocking GUI."""
        if not self.icon:
            self._init_tray()
        try:
            self.icon.run_detached()
        except Exception:
            pass

    def _init_tray(self):
        img = self._get_icon_image()
        self.icon = pystray.Icon(
            name="RiotLink",
            icon=img,
            title="Riot Link",
            menu=self._build_menu()
        )

    def stop(self):
        """Stop and remove icon from system tray."""
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None

    def notify(self, title: str, message: str):
        """Display Windows balloon notification from tray icon."""
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass
