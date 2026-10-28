"""
Single Instance Application Manager for Riot Link.
Ensures only one instance of the application runs at any time on Windows.
If another instance is launched:
1. Detects the existing instance via a Win32 Named Mutex.
2. Transmits an activation signal over a loopback TCP socket.
3. Restores and brings the existing window to the foreground (even if minimized to tray).
4. Terminates the duplicate instance immediately.
"""

import ctypes
import os
import socket
import sys
import time
import atexit
import threading
from pathlib import Path
from typing import Callable, Optional

from .config import Config


ERROR_ALREADY_EXISTS = 183


class SingleInstanceManager:
    MUTEX_NAME = "Local\\RiotLink_SingleInstance_Mutex"

    def __init__(self):
        self._mutex_handle = None
        self._server_socket: Optional[socket.socket] = None
        self._is_listener_running = False
        self._on_restore_callback: Optional[Callable[[], None]] = None
        self._cleaned_up = False

    @property
    def port_file(self) -> Path:
        return Config.APP_DATA_DIR / "app.port"

    def is_already_running(self) -> bool:
        """
        Check if an instance is already running.
        If yes, notifies it to restore itself and returns True.
        If no, holds the mutex and returns False.
        """
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.CreateMutexW(None, False, self.MUTEX_NAME)
            last_err = kernel32.GetLastError()

            if last_err == ERROR_ALREADY_EXISTS:
                if handle:
                    kernel32.CloseHandle(handle)
                # Another instance is actively running; signal it to restore
                self.notify_running_instance()
                return True

            # This process is the primary instance
            self._mutex_handle = handle
            atexit.register(self.cleanup)
            return False
        except Exception:
            # Fallback in case of unexpected environment constraint
            return False

    def notify_running_instance(self, timeout_sec: float = 2.0) -> bool:
        """
        Signal the existing instance via localhost TCP to restore its window.
        Retries briefly in case the primary instance is currently starting up.
        """
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            if self.port_file.is_file():
                try:
                    with open(self.port_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    if content.isdigit():
                        port = int(content)
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                            client.settimeout(1.2)
                            client.connect(("127.0.0.1", port))
                            client.sendall(b"RESTORE\n")
                            resp = client.recv(16)
                            if b"OK" in resp:
                                return True
                except Exception:
                    pass
            time.sleep(0.1)

        # Fallback Win32 window restoration if socket is unreachable
        self._restore_fallback_win32()
        return False

    def _restore_fallback_win32(self):
        """Fallback attempt to bring the window to front using Win32 API."""
        try:
            user32 = ctypes.windll.user32
            # Find window by title starting with Config.APP_NAME
            title_prefix = Config.APP_NAME.lower()

            def enum_proc(hwnd, lparam):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if title_prefix in buff.value.lower():
                        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                        user32.SetForegroundWindow(hwnd)
                        return False
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
        except Exception:
            pass

    def start_listener(self, on_restore: Callable[[], None]):
        """
        Start the loopback socket listener server on an OS-assigned ephemeral port.
        """
        self._on_restore_callback = on_restore
        try:
            Config.APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Bind to 127.0.0.1 with port 0 (OS automatically assigns an available port)
            self._server_socket.bind(("127.0.0.1", 0))
            self._server_socket.listen(5)
            port = self._server_socket.getsockname()[1]

            with open(self.port_file, "w", encoding="utf-8") as f:
                f.write(str(port))

            self._is_listener_running = True
            thread = threading.Thread(
                target=self._listen_loop,
                daemon=True,
                name="SingleInstanceListenerThread"
            )
            thread.start()
        except Exception:
            pass

    def _listen_loop(self):
        while self._is_listener_running and self._server_socket:
            try:
                conn, _ = self._server_socket.accept()
                with conn:
                    conn.settimeout(2.0)
                    data = conn.recv(64)
                    if b"RESTORE" in data:
                        if self._on_restore_callback:
                            try:
                                self._on_restore_callback()
                            except Exception:
                                pass
                        conn.sendall(b"OK\n")
            except Exception:
                if not self._is_listener_running:
                    break

    def cleanup(self):
        """Release resources on application exit."""
        if self._cleaned_up:
            return
        self._cleaned_up = True
        self._is_listener_running = False

        # Remove port file
        try:
            if self.port_file.is_file():
                self.port_file.unlink()
        except Exception:
            pass

        # Close server socket
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

        # Release mutex handle
        if self._mutex_handle:
            try:
                ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
            except Exception:
                pass
            self._mutex_handle = None
