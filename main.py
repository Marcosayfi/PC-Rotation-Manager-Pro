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

import uvicorn
from PyQt6.QtCore import QSharedMemory
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from backend.server import create_app
from backend.state_manager import StateManager
from ui.main_window import MainWindow

SERVER_NAME = "PCRotationManagerPro-Local"
DATA_DIR = Path("C:\\PCRotationManagerPro")


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