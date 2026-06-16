"""Main PyQt6 window for PC Rotation Manager Pro."""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QMenu,
    QProgressBar,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from backend.state_manager import MAX_BREAK_TOKENS, StateManager
from ui.admin_panel import AdminPanel
from ui.alarm import AlarmPlayer
from ui.break_dialog import BreakDialog
from ui.notifications import send_alarm_notification


def format_time(minutes: float) -> str:
    total_sec = max(0, int(minutes * 60))
    h, rem = divmod(total_sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class PlayerCard(QFrame):
    def __init__(self, title: str, color: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("playerCard")
        self._active = False
        self._color = color

        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(self.title)

        self.timer_label = QLabel("02:05:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setFont(QFont("Consolas", 36, QFont.Weight.Bold))
        layout.addWidget(self.timer_label)

        self.finish_time_label = QLabel("Finish: ~14:30")
        self.finish_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.finish_time_label.setStyleSheet("color: #b0b0b0; font-size: 10px;")
        layout.addWidget(self.finish_time_label)

        self.break_label = QLabel("Break tokens: 3/3")
        self.break_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.break_label)

        self.break_bar = QProgressBar()
        self.break_bar.setRange(0, 3)
        self.break_bar.setFormat("%v / 3 tokens")
        layout.addWidget(self.break_bar)

        self._apply_style()

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply_style()

    def _apply_style(self) -> None:
        border = f"3px solid {self._color}" if self._active else "2px solid #444"
        bg = "#1a2a1a" if self._active else "#1e1e1e"
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border: {border}; border-radius: 12px; padding: 8px; }}"
            "QLabel { color: #f0f0f0; }"
        )


class MainWindow(QMainWindow):
    def __init__(self, state_manager: StateManager) -> None:
        super().__init__()
        self.state_manager = state_manager
        self.alarm = AlarmPlayer()

        state_manager.on_alarm = self._on_alarm
        state_manager.on_alarm_clear = self.alarm.stop
        state_manager.on_state_change = self._refresh_ui

        self.setWindowTitle("PC Rotation Manager Pro")
        self.setMinimumSize(720, 520)
        self._set_window_icon()
        self._build_ui()
        self._setup_shortcuts()
        self._setup_tray()

        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._refresh_ui)
        self._ui_timer.start(500)

        self._refresh_ui()
        if self.state_manager.get_status().get("alarm_active"):
            self.alarm.start()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)

        header = QLabel("PC Rotation Manager Pro")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        root.addWidget(header)

        self.server_label = QLabel()
        self.server_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.server_label.setStyleSheet("color: #8ab4f8;")
        root.addWidget(self.server_label)

        cards = QHBoxLayout()
        self.p1_card = PlayerCard("Player 1", "#4caf50")
        self.p2_card = PlayerCard("Player 2", "#2196f3")
        cards.addWidget(self.p1_card)
        cards.addWidget(self.p2_card)
        root.addLayout(cards)

        status_row = QHBoxLayout()
        self.active_label = QLabel("Active: Player 1")
        self.active_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        status_row.addWidget(self.active_label)

        self.break_status = QLabel("")
        status_row.addWidget(self.break_status)
        status_row.addStretch()

        self.stopwatch_label = QLabel("Stopwatch: OFF")
        status_row.addWidget(self.stopwatch_label)
        root.addLayout(status_row)

        self.alarm_banner = QLabel("⏰ TIME UP — Dismiss alarm to continue")
        self.alarm_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alarm_banner.setStyleSheet(
            "background: #c0392b; color: white; padding: 10px; font-weight: bold; border-radius: 6px;"
        )
        self.alarm_banner.hide()
        root.addWidget(self.alarm_banner)

        dismiss_btn = QPushButton("Dismiss Alarm")
        dismiss_btn.clicked.connect(self._dismiss_alarm)
        dismiss_btn.setStyleSheet("background: #e74c3c; color: white; padding: 8px;")
        self.dismiss_btn = dismiss_btn
        self.dismiss_btn.hide()
        root.addWidget(self.dismiss_btn)

        btn_grid = QGridLayout()
        self.switch_btn = QPushButton("Switch Player")
        self.switch_btn.clicked.connect(self._switch_player)
        btn_grid.addWidget(self.switch_btn, 0, 0)

        self.break_btn = QPushButton("Start Break")
        self.break_btn.clicked.connect(self._toggle_break)
        btn_grid.addWidget(self.break_btn, 0, 1)

        self.admin_btn = QPushButton("🔧 Admin Panel")
        self.admin_btn.clicked.connect(self._open_admin)
        btn_grid.addWidget(self.admin_btn, 1, 0)

        spacer = QWidget()
        btn_grid.addWidget(spacer, 1, 1)
        root.addLayout(btn_grid)

        self.log_preview = QGroupBox("Recent Activity")
        log_layout = QVBoxLayout(self.log_preview)
        self.log_label = QLabel("")
        self.log_label.setWordWrap(True)
        self.log_label.setStyleSheet("color: #aaa; font-family: Consolas;")
        log_layout.addWidget(self.log_label)
        root.addWidget(self.log_preview)

        self.setStyleSheet("QMainWindow, QWidget { background: #121212; color: #eee; }")

    def _setup_shortcuts(self) -> None:
        pass  # Admin panel is now accessible via button

    def _on_alarm(self) -> None:
        active_player = self.state_manager.state.active_player
        send_alarm_notification(active_player)
        self.alarm.start()
        self._refresh_ui()

    def _dismiss_alarm(self) -> None:
        self.state_manager.dismiss_alarm()

    def _open_admin(self) -> None:
        # Check if both secret codes are set
        p1_secret = self.state_manager.get_secret_code(1)
        p2_secret = self.state_manager.get_secret_code(2)
        
        # If codes are not set yet, allow access to set them (first-time setup)
        if not p1_secret or not p2_secret:
            self.state_manager.logger.log("Admin mode accessed (first-time setup)")
            dlg = AdminPanel(self.state_manager, self)
            dlg.exec()
            self._refresh_ui()
            return
        
        # If codes are set, require verification
        code1, ok1 = self._prompt_code("Player 1 Secret Code:")
        if not ok1 or not code1:
            return
        
        code2, ok2 = self._prompt_code("Player 2 Secret Code:")
        if not ok2 or not code2:
            return
        
        # Verify both codes
        if not self.state_manager.verify_both_secrets(code1, code2):
            QMessageBox.critical(self, "Access Denied", "Invalid secret codes.")
            self.state_manager.logger.log("Admin mode access denied — invalid codes")
            return
        
        self.state_manager.logger.log("Admin mode accessed")
        dlg = AdminPanel(self.state_manager, self)
        dlg.exec()
        self._refresh_ui()

    def _prompt_code(self, prompt: str) -> tuple[str, bool]:
        """Show a password input dialog and return (code, ok)."""
        code, ok = QInputDialog.getText(
            self,
            "Admin Access Required",
            prompt,
            QLineEdit.EchoMode.Password
        )
        return (code, ok)

    def _switch_player(self) -> None:
        ok, msg = self.state_manager.switch_player()
        if not ok:
            QMessageBox.warning(self, "Cannot Switch", msg)

    def _toggle_break(self) -> None:
        status = self.state_manager.get_status()
        if status["on_break"]:
            ok, msg = self.state_manager.stop_break()
            if not ok:
                QMessageBox.warning(self, "Break", msg)
            return

        dlg = BreakDialog(self, self.state_manager)
        if dlg.exec() and dlg.get_reason():
            if dlg.is_unfair():
                codes = dlg.get_secret_codes()
                if codes:
                    ok, msg = self.state_manager.start_unfair_break(dlg.get_reason(), codes[0], codes[1])
                    if not ok:
                        QMessageBox.warning(self, "Unfair Break Failed", msg)
            else:
                ok, msg = self.state_manager.start_break(dlg.get_reason())
                if not ok:
                    QMessageBox.warning(self, "Break", msg)

    def _refresh_ui(self) -> None:
        sm = self.state_manager
        status = sm.get_status()
        ip = sm.advertised_ip
        port = sm.server_port
        self.server_label.setText(
            f"Mobile dashboard: http://{ip}:{port}/  |  API: /status  /logs"
        )

        p1_time = status["player1_time"]
        p2_time = status["player2_time"]
        self.p1_card.timer_label.setText(format_time(p1_time))
        self.p2_card.timer_label.setText(format_time(p2_time))
        
        # Update break tokens display
        p1_tokens = status["break_tokens_p1"]
        p2_tokens = status["break_tokens_p2"]
        self.p1_card.break_label.setText(f"Break tokens: {p1_tokens}/3")
        self.p2_card.break_label.setText(f"Break tokens: {p2_tokens}/3")
        self.p1_card.break_bar.setValue(p1_tokens)
        self.p2_card.break_bar.setValue(p2_tokens)

        # Calculate and display estimated finish times for both players
        from datetime import datetime, timedelta
        import time as time_module
        
        active = status["active_player"]
        now = time_module.time()
        session_elapsed = (now - sm.state.session_started_at) / 60.0  # in minutes
        
        # Show finish time for Player 1 (if they have time remaining)
        if p1_time > 0:
            est_finish_dt = datetime.now() + timedelta(minutes=p1_time)
            finish_str = est_finish_dt.strftime("%H:%M")
            self.p1_card.finish_time_label.setText(f"Finishes at: {finish_str}")
        else:
            self.p1_card.finish_time_label.setText("Time's up!")
            
        # Show finish time for Player 2 (if they have time remaining)
        if p2_time > 0:
            est_finish_dt = datetime.now() + timedelta(minutes=p2_time)
            finish_str = est_finish_dt.strftime("%H:%M")
            self.p2_card.finish_time_label.setText(f"Finishes at: {finish_str}")
        else:
            self.p2_card.finish_time_label.setText("Time's up!")

        self.p1_card.set_active(active == 1)
        self.p2_card.set_active(active == 2)
        self.active_label.setText(f"Active: Player {active}  |  Session: {int(session_elapsed)} min")

        if status["on_break"]:
            reason = status.get("break_reason", "")
            unfair = " (UNFAIR)" if status.get("unfair_break_approved") else ""
            self.break_status.setText(f"⏸ ON BREAK ({reason}){unfair} — timer paused")
            self.break_status.setStyleSheet("color: #f1c40f; font-weight: bold;")
            self.break_btn.setText("Stop Break")
        else:
            self.break_status.setText("")
            self.break_status.setStyleSheet("")
            self.break_btn.setText("Start Break")

        if status["stopwatch_mode"]:
            sw = status["stopwatch_minutes"]
            self.stopwatch_label.setText(f"⏱ Stopwatch: {format_time(sw)} (P1 extra → P2 bonus)")
            self.stopwatch_label.setStyleSheet("color: #e67e22; font-weight: bold;")
        else:
            self.stopwatch_label.setText("Stopwatch: OFF")
            self.stopwatch_label.setStyleSheet("color: #888;")

        alarm = status.get("alarm_active", False)
        self.alarm_banner.setVisible(alarm)
        self.dismiss_btn.setVisible(alarm)

        low_style = "color: #e74c3c;"
        for card, time_val, depleted in [
            (self.p1_card, status["player1_time"], status.get("player1_depleted")),
            (self.p2_card, status["player2_time"], status.get("player2_depleted")),
        ]:
            if time_val <= 5 or depleted:
                card.timer_label.setStyleSheet(low_style)
            else:
                card.timer_label.setStyleSheet("color: #f0f0f0;")

        recent = sm.logger.get_recent(8)
        self.log_label.setText("\n".join(recent))

    def _ico_path(self, ext: str = "ico") -> str:
        """Return absolute path to icon.{ext} in the project root."""
        # main_window.py is in ui/, so go up one level for the project root
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", f"icon.{ext}"
        )

    def _set_window_icon(self) -> None:
        """Set the window/taskbar icon (Windows needs .ico for taskbar)."""
        ico = self._ico_path("ico")
        png = self._ico_path("png")
        icon_file = ico if os.path.exists(ico) else png
        if os.path.exists(icon_file):
            self.setWindowIcon(QIcon(icon_file))

    def _setup_tray(self) -> None:
        """Create the system tray icon with context menu."""
        ico = self._ico_path("ico")
        png = self._ico_path("png")
        ipath = ico if os.path.exists(ico) else png
        if os.path.exists(ipath):
            self.tray_icon = QSystemTrayIcon(QIcon(ipath), self)
        else:
            # Fallback: create a simple colored square
            pm = QPixmap(32, 32)
            pm.fill(QColor("#4caf50"))
            self.tray_icon = QSystemTrayIcon(QIcon(pm), self)

        self.tray_icon.setToolTip("PC Rotation Manager Pro")

        # Build context menu
        tray_menu = QMenu()
        open_action = QAction("Open", self)
        open_action.triggered.connect(self._show_window)
        tray_menu.addAction(open_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

    def _tray_activated(self, reason: int) -> None:
        """Left-click on tray icon shows the window."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._show_window()

    def _show_window(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_app(self) -> None:
        self.alarm.stop()
        self.state_manager.stop()
        self.tray_icon.hide()
        QApplication.quit()

    def changeEvent(self, event) -> None:
        """Intercept minimize to hide to tray instead of taskbar."""
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized():
                self.hide()
                self.tray_icon.showMessage(
                    "PC Rotation Manager",
                    "Still running — double-click tray icon to reopen.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000,
                )
        super().changeEvent(event)

    def closeEvent(self, event) -> None:
        """Close button hides to tray instead of quitting."""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "PC Rotation Manager",
            "Minimized to tray — right-click icon and select Quit to exit.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )
