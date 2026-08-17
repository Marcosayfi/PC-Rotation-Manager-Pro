"""Standalone timer editor styled like PC Rotation Manager Pro main window."""

import json
import math
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

STATE_FILE = Path(r"C:\PCRotationManagerPro\state.json")
ICON_FILE = Path(__file__).resolve().parent / "icon.ico"


def fmt(minutes: float) -> str:
    total_sec = max(0, math.ceil(minutes * 60))
    h, rem = divmod(total_sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def load_state() -> dict | None:
    if not STATE_FILE.exists():
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_state(data: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class PlayerEditCard(QFrame):
    def __init__(self, title: str, color: str, parent=None) -> None:
        super().__init__(parent)
        self._color = color
        self._active = False

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        layout.addWidget(self.title)

        self.preview_label = QLabel("02:05:00")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFont(QFont("Consolas", 24, QFont.Weight.Bold))
        layout.addWidget(self.preview_label)

        self.spin = QDoubleSpinBox()
        self.spin.setRange(0, 999)
        self.spin.setDecimals(1)
        self.spin.setSuffix(" min")
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        layout.addWidget(self.spin)

        self.apply_style()

    def set_active(self, active: bool) -> None:
        self._active = active
        self.apply_style()

    def apply_style(self) -> None:
        border = f"3px solid {self._color}" if self._active else "2px solid #444"
        bg = "#1a2a1a" if self._active else "#1e1e1e"
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border: {border}; border-radius: 12px; }}"
            "QLabel { color: #f0f0f0; border: none; background: transparent; }"
            "QDoubleSpinBox { background: #2a2a2a; color: #f0f0f0; border: 1px solid #555;"
            "  border-radius: 6px; padding: 4px; }"
            "QDoubleSpinBox:focus { border: 1px solid #8ab4f8; }"
        )


class TimerEditor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Edit Timers — PC Rotation Manager Pro")
        self.setMinimumSize(620, 380)
        self.active_player = 1

        if ICON_FILE.exists():
            self.setWindowIcon(QIcon(str(ICON_FILE)))

        self.setStyleSheet(
            "QWidget { background: #121212; color: #f0f0f0; font-family: 'Segoe UI', sans-serif; }"
            "QPushButton { background: #2a2a2a; color: #f0f0f0; border: 1px solid #444;"
            "  border-radius: 8px; padding: 8px 14px; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background: #333; border-color: #666; }"
            "QPushButton#switchBtn { background: #e67e22; border: none; color: white; }"
            "QPushButton#switchBtn:hover { background: #d35400; }"
            "QPushButton#saveBtn { background: #4caf50; border: none; color: white; }"
            "QPushButton#saveBtn:hover { background: #43a047; }"
            "QPushButton#reloadBtn { background: #2196f3; border: none; color: white; }"
            "QPushButton#reloadBtn:hover { background: #1e88e5; }"
        )

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(18, 16, 18, 16)

        header = QLabel("PC Rotation Manager Pro — Quick Editor")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        root.addWidget(header)

        self.status_label = QLabel("Loading state...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #8ab4f8; font-size: 11px;")
        root.addWidget(self.status_label)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.p1_card = PlayerEditCard("Player 1", "#4caf50")
        self.p2_card = PlayerEditCard("Player 2", "#2196f3")

        cards_layout.addWidget(self.p1_card)
        cards_layout.addWidget(self.p2_card)
        root.addLayout(cards_layout)

        self.p1_card.spin.valueChanged.connect(self._update_previews)
        self.p2_card.spin.valueChanged.connect(self._update_previews)

        status_row = QHBoxLayout()
        self.active_status = QLabel("Active: Player 1")
        self.active_status.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        status_row.addWidget(self.active_status)
        status_row.addStretch()

        self.switch_btn = QPushButton("Switch Active Player")
        self.switch_btn.setObjectName("switchBtn")
        self.switch_btn.clicked.connect(self._switch_player)
        status_row.addWidget(self.switch_btn)
        root.addLayout(status_row)

        root.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        reload_btn = QPushButton("Reload")
        reload_btn.setObjectName("reloadBtn")
        reload_btn.clicked.connect(self._load)
        btn_row.addWidget(reload_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        root.addLayout(btn_row)

        self._load()

        self._auto_reload = QTimer(self)
        self._auto_reload.timeout.connect(self._load_silent)
        self._auto_reload.start(5000)

    def _update_previews(self) -> None:
        p1 = self.p1_card.spin.value()
        p2 = self.p2_card.spin.value()
        self.p1_card.preview_label.setText(fmt(p1))
        self.p2_card.preview_label.setText(fmt(p2))

        low = "color: #e74c3c;"
        self.p1_card.preview_label.setStyleSheet(low if p1 <= 5 else "color: #f0f0f0;")
        self.p2_card.preview_label.setStyleSheet(low if p2 <= 5 else "color: #f0f0f0;")

    def _update_active_ui(self) -> None:
        self.p1_card.set_active(self.active_player == 1)
        self.p2_card.set_active(self.active_player == 2)
        color = "#4caf50" if self.active_player == 1 else "#2196f3"
        self.active_status.setText(f"Active: Player {self.active_player}")
        self.active_status.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

    def _switch_player(self) -> None:
        self.active_player = 2 if self.active_player == 1 else 1
        self._update_active_ui()

    def _load(self) -> None:
        data = load_state()
        if data is None:
            self.status_label.setText("state.json not found — run main app first")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
            return

        self.p1_card.spin.setValue(float(data.get("player1_time", 125)))
        self.p2_card.spin.setValue(float(data.get("player2_time", 125)))
        self.active_player = int(data.get("active_player", 1))

        self._update_active_ui()
        self._update_previews()
        self.status_label.setText(f"Loaded from {STATE_FILE}")
        self.status_label.setStyleSheet("color: #8ab4f8; font-size: 11px;")

    def _load_silent(self) -> None:
        if not self.p1_card.spin.hasFocus() and not self.p2_card.spin.hasFocus():
            self._load()

    def _save(self) -> None:
        data = load_state()
        if data is None:
            QMessageBox.warning(self, "Error", f"State file not found:\n{STATE_FILE}")
            return

        p1 = self.p1_card.spin.value()
        p2 = self.p2_card.spin.value()

        data["player1_time"] = p1
        data["player2_time"] = p2
        data["player1_depleted"] = p1 <= 0
        data["player2_depleted"] = p2 <= 0
        data["active_player"] = self.active_player

        save_state(data)
        self.status_label.setText("Saved! Takes effect in ~7s.")
        self.status_label.setStyleSheet("color: #4caf50; font-size: 11px;")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PC Rotation Timer Editor")
    editor = TimerEditor()
    editor.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())