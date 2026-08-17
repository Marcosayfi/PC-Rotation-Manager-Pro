"""PC Rotation Manager Pro — entry point."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

# Suppress console output if running with pythonw
if sys.executable.endswith("pythonw.exe"):
    # Redirect stdout and stderr to suppress output
    class NullWriter:
        def write(self, s):
            pass
        def flush(self):
            pass
    
    # Only suppress uvicorn logs, keep errors
    os.environ["PYTHONUNBUFFERED"] = "1"

import faulthandler
import threading
import traceback

import uvicorn
from PyQt6.QtCore import QSharedMemory
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from backend.discord_bot import DiscordBotRunner
from backend.server import create_app
from backend.state_manager import StateManager
from ui.main_window import MainWindow

SERVER_NAME = "PCRotationManagerPro-Local"
DATA_DIR = Path("C:\\PCRotationManagerPro")

# ---------------------------------------------------------------------------
# Crash capture: turn silent exits (hidden console) into a readable crash.log
# so "app closes by itself" becomes a diagnosed traceback.
# ---------------------------------------------------------------------------
CRASH_LOG = DATA_DIR / "crash.log"


def _open_crash_log():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return open(CRASH_LOG, "w", encoding="utf-8", buffering=1)
    except OSError:
        return None


_crash_handle = _open_crash_log()

if _crash_handle is not None:
    try:
        faulthandler.enable(_crash_handle)
    except Exception:
        _crash_handle = None


def _write_crash(prefix: str, exc) -> None:
    if _crash_handle is None:
        return
    try:
        _crash_handle.write(f"===== {prefix}: {type(exc).__name__}: {exc} =====\n")
        _crash_handle.flush()
    except Exception:
        pass


def _report_exception(label: str, etype, value, tb) -> None:
    if _crash_handle is not None:
        try:
            _crash_handle.write(f"===== {label} thread died =====\n")
            traceback.print_exception(etype, value, tb, file=_crash_handle)
            _crash_handle.flush()
        except Exception:
            pass


def _main_thread_excepthook(etype, value, tb) -> None:
    _report_exception("main", etype, value, tb)


def _thread_excepthook(args) -> None:
    _write_crash("thread", args.exc_value)
    if _crash_handle is not None:
        try:
            _crash_handle.write(f"===== background thread died =====\n")
            traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=_crash_handle)
            _crash_handle.flush()
        except Exception:
            pass


sys.excepthook = _main_thread_excepthook
threading.excepthook = _thread_excepthook


def run_server(state_manager: StateManager) -> None:
    app = create_app(state_manager)
    config = uvicorn.Config(
        app,
        host=state_manager.server_host,
        port=state_manager.server_port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.run()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PC Rotation Manager Pro")
    app.setOrganizationName("PCRotationManager")
    # Critical: never let the app quit when its last window is hidden to the
    # tray. Without this, losing/absent tray icon + hidden window = silent quit.
    app.setQuitOnLastWindowClosed(False)

    # ---- Single-instance lock using QSharedMemory + QLocalServer ----
    shm = QSharedMemory("PCRotationManagerPro-Instance")
    if shm.attach():
        # Another instance is already running — tell it to show its window
        sock = QLocalSocket()
        sock.connectToServer(SERVER_NAME)
        if sock.waitForConnected(1000):
            sock.write(b"show")
            sock.waitForBytesWritten(1000)
            sock.disconnectFromServer()
        return 0

    shm.create(1)

    # Local server to receive "show" commands from duplicate launches
    local_server = QLocalServer()
    local_server.removeServer(SERVER_NAME)
    local_server.listen(SERVER_NAME)

    state_manager = StateManager(DATA_DIR)
    state_manager.start()

    server_thread = threading.Thread(
        target=run_server,
        args=(state_manager,),
        daemon=True,
        name="api-server",
    )
    server_thread.start()

    if state_manager.discord_bot_token:
        bot = DiscordBotRunner(
            state_manager=state_manager,
            token=state_manager.discord_bot_token,
            guild_id=state_manager.discord_guild_id,
        )
        bot_thread = threading.Thread(
            target=bot.start,
            daemon=True,
            name="discord-bot",
        )
        bot_thread.start()

    window = MainWindow(state_manager)

    def on_new_connection() -> None:
        client = local_server.nextPendingConnection()
        if client:
            client.readAll()  # discard the "show" message
            window.showNormal()
            window.activateWindow()
            window.raise_()
            client.disconnectFromServer()

    local_server.newConnection.connect(on_new_connection)
    window.show()

    code = app.exec()
    state_manager.stop()
    shm.detach()
    local_server.close()
    return code


if __name__ == "__main__":
    sys.exit(main())