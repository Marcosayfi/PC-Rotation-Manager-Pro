"""Action logging for PC Rotation Manager Pro."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path


class ActionLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.log_path.exists():
            self.log_path.touch()

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M")
        line = f"{timestamp} {message}\n"
        with self._lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line)

    def get_recent(self, count: int = 50) -> list[str]:
        with self._lock:
            if not self.log_path.exists():
                return []
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\n") for line in f if line.strip()]
        return lines[-count:]

    def get_all(self) -> list[str]:
        with self._lock:
            if not self.log_path.exists():
                return []
            with open(self.log_path, "r", encoding="utf-8") as f:
                return [line.rstrip("\n") for line in f if line.strip()]
