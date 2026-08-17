"""About dialog for PC Rotation Manager Pro."""

from __future__ import annotations

import os
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from backend.state_manager import StateManager


class AboutDialog(QDialog):
    def __init__(self, state_manager: StateManager, parent=None) -> None:
        super().__init__(parent)
        self.state_manager = state_manager
        self.setWindowTitle("About — PC Rotation Manager Pro")
        self.setFixedSize(520, 420)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Header card
        header_card = QFrame()
        header_card.setStyleSheet("background: #1e1e1e; border: 1px solid #333; border-radius: 8px; padding: 12px;")
        h_layout = QHBoxLayout(header_card)

        # App Icon
        icon_label = QLabel()
        icon_path = Path(__file__).resolve().parent.parent / "icon.png"
        if not icon_path.exists():
            icon_path = Path(__file__).resolve().parent.parent / "icon.ico"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path)).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        else:
            icon_label.setText("⏰")
            icon_label.setFont(QFont("Segoe UI Emoji", 36))
        h_layout.addWidget(icon_label)

        title_vbox = QVBoxLayout()
        app_title = QLabel("PC Rotation Manager Pro")
        app_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_vbox.addWidget(app_title)

        version_label = QLabel("Version 1.0.0 Pro")
        version_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        title_vbox.addWidget(version_label)

        subtitle = QLabel("Fair Gaming Rotation & Session Management System")
        subtitle.setStyleSheet("color: #aaa; font-size: 11px;")
        title_vbox.addWidget(subtitle)

        h_layout.addLayout(title_vbox)
        layout.addWidget(header_card)

        # Description
        desc = QLabel(
            "PC Rotation Manager Pro ensures balanced playtime, automated break enforcement, "
            "and cross-device mobile status monitoring for shared gaming computers."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #ccc; font-size: 12px; line-height: 1.4;")
        layout.addWidget(desc)

        # System Information Details
        info_frame = QFrame()
        info_frame.setStyleSheet("background: #141414; border: 1px solid #282828; border-radius: 6px; padding: 8px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(4)

        sm = self.state_manager
        info_rows = [
            ("Mobile Dashboard", f"http://{sm.advertised_ip}:{sm.server_port}/"),
            ("Shared Data Dir", str(sm.data_dir)),
            ("User Settings", str(sm.settings_manager.settings_path)),
        ]

        for label_text, val_text in info_rows:
            row = QHBoxLayout()
            lbl = QLabel(f"{label_text}:")
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #8ab4f8; min-width: 120px;")
            val = QLabel(val_text)
            val.setStyleSheet("color: #ddd; font-family: Consolas; font-size: 11px;")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(lbl)
            row.addWidget(val, 1)
            info_layout.addLayout(row)

        layout.addWidget(info_frame)

        layout.addStretch()

        # Close button
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("background: #333; color: white; padding: 6px 20px; border-radius: 4px;")
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)

        self.setStyleSheet(
            "QDialog { background: #181818; color: #eee; }"
            "QLabel { color: #eee; }"
        )
