"""Main PyQt6 window for PC Rotation Manager Pro."""

from __future__ import annotations

import math
import os
import time

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
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
from ui.about_dialog import AboutDialog
from ui.admin_panel import AdminPanel
from ui.alarm import AlarmPlayer, resolve_alarm_sound_path
from ui.break_dialog import BreakDialog
from ui.notifications import send_alarm_notification, send_time_alert_notification, send_windows_notification
from ui.settings_dialog import SettingsDialog


def format_time(minutes: float) -> str:
    total_sec = max(0, math.ceil(minutes * 60))
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

        self.break_label = QLabel("Break tokens: 2/2")
        self.break_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.break_label)

        self.break_bar = QProgressBar()
        self.break_bar.setRange(0, 2)
        self.break_bar.setFormat("%v / 2 tokens")
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
    alarm_requested = pyqtSignal()
    alarm_clear_requested = pyqtSignal()
    state_changed = pyqtSignal()

    def __init__(self, state_manager: StateManager) -> None:
        super().__init__()
        self.state_manager = state_manager
        self.alarm = AlarmPlayer()

        self.alarm_requested.connect(self._on_alarm)
        self.alarm_clear_requested.connect(self.alarm.stop)
        self.state_changed.connect(self._refresh_ui)
        state_manager.on_alarm = self._request_alarm
        state_manager.on_alarm_clear = self._request_alarm_clear
        state_manager.on_state_change = self._request_state_change

        self.setWindowTitle("PC Rotation Manager Pro")
        self.setMinimumSize(720, 520)
        self._set_window_icon()
        self._build_ui()
        self._setup_shortcuts()
        self._setup_tray()

        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._refresh_ui)
        self._ui_timer.start(250)

        self._refresh_ui()
        if self.state_manager.get_status().get("alarm_active"):
            self.alarm.start(self._current_alarm_sound_path())

    def _request_alarm(self) -> None:
        self.alarm_requested.emit()

    def _request_alarm_clear(self) -> None:
        self.alarm_clear_requested.emit()

    def _request_state_change(self) -> None:
        self.state_changed.emit()

    def _safe_slot(self, name: str, fn, *args, **kwargs):
        """Run a Qt slot so an uncaught exception cannot abort the process.
        In PyQt6 an exception escaping a slot kills the app with no traceback
        (hidden console => looks like 'the app closed by itself')."""
        try:
            return fn(*args, **kwargs)
        except BaseException as e:
            import traceback
            tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            self.state_manager.logger.log(f"INTERNAL ERROR in {name}: {e}")
            try:
                with open(r"C:\PCRotationManagerPro\crash.log", "a", encoding="utf-8") as f:
                    f.write(f"===== {name} slot error =====\n{tb}\n")
            except OSError:
                pass
            try:
                QMessageBox.critical(
                    self,
                    "PC Rotation Manager Pro",
                    f"An internal error occurred ({name}):\n\n{type(e).__name__}: {e}\n\n"
                    "The app will keep running. Details saved to C:\\PCRotationManagerPro\\crash.log.",
                )
            except BaseException:
                pass

    def _current_alarm_sound_path(self):
        settings = self.state_manager.user_settings
        return resolve_alarm_sound_path(settings.alarm_sound_id, settings.custom_alarm_sounds)

    def _build_ui(self) -> None:
        self._setup_menu_bar()

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

        self.setStyleSheet(
            "QMainWindow, QWidget { background: #121212; color: #eee; }"
            "QMenuBar { background-color: #121212; color: #eee; border: none; padding: 2px 6px; font-size: 13px; }"
            "QMenuBar::item { background: transparent; padding: 4px 10px; border-radius: 6px; }"
            "QMenuBar::item:selected { background-color: #2b2b2b; color: #ffffff; }"
            "QMenuBar::item:pressed { background-color: #383838; }"
            "QMenu { background-color: #2b2b2b; color: #ffffff; border: 1px solid #3d3d3d; border-radius: 8px; padding: 4px; font-size: 13px; }"
            "QMenu::item { background: transparent; padding: 6px 20px; border-radius: 6px; margin: 1px 2px; }"
            "QMenu::item:selected { background-color: #3d3d3d; color: #ffffff; }"
            "QMenu::separator { height: 1px; background: #3d3d3d; margin: 4px 6px; }"
        )

    def _setup_menu_bar(self) -> None:
        menubar = self.menuBar()
        menubar.clear()

        # File Menu
        file_menu = menubar.addMenu("&File")

        settings_action = QAction("Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        about_action = QAction("About", self)
        about_action.setShortcut(QKeySequence("F1"))
        about_action.triggered.connect(self._open_about)
        file_menu.addAction(about_action)

        file_menu.addSeparator()

        exit_action = QAction("Quit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self._quit_app)
        file_menu.addAction(exit_action)

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.state_manager, self)
        dlg.exec()
        self._refresh_ui()

    def _open_about(self) -> None:
        dlg = AboutDialog(self.state_manager, self)
        dlg.exec()

    def _setup_shortcuts(self) -> None:
        pass  # Shortcuts configured via menu actions

    def _on_alarm(self) -> None:
        self._safe_slot("_on_alarm", self._on_alarm_impl)

    def _on_alarm_impl(self) -> None:
        user_cfg = self.state_manager.user_settings
        active_player = self.state_manager.state.active_player
        reason = self.state_manager.state.alarm_reason
        self.alarm.start(self._current_alarm_sound_path())

        # If window is minimized or hidden in tray, unhide and bring to front
        if self.isHidden() or self.isMinimized():
            self.showNormal()
            self.activateWindow()
            self.raise_()

        if "Remaining Alert" in reason:
            if user_cfg.time_alert_toast_enabled:
                send_windows_notification("⏰ PC Rotation Manager — Time Alert", f"{reason}! Click to dismiss.")
        else:
            if user_cfg.time_up_toast_enabled:
                send_alarm_notification(active_player)

        self._refresh_ui()

    def _dismiss_alarm(self) -> None:
        self._safe_slot("_dismiss_alarm", self.state_manager.dismiss_alarm)

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

    def _display_minutes(self, stored_minutes: float, is_active: bool, on_break: bool) -> float:
        """Interpolate remaining time between background ticks for smooth display."""
        if not is_active or on_break:
            return stored_minutes
        sm = self.state_manager
        elapsed_min = max(0.0, (time.time() - sm.state.last_tick) / 60.0)
        return max(0.0, stored_minutes - elapsed_min)

    def _refresh_ui(self) -> None:
        self._safe_slot("_refresh_ui", self._refresh_ui_impl)

    def _refresh_ui_impl(self) -> None:
        sm = self.state_manager
        status = sm.get_status()
        ip = sm.advertised_ip
        port = sm.server_port
        self.server_label.setText(
            f"Mobile dashboard: http://{ip}:{port}/  |  API: /status  /logs"
        )

        on_break = status["on_break"]
        active = status["active_player"]
        p1_time = self._display_minutes(
            status["player1_time"], active == 1, on_break
        )
        p2_time = self._display_minutes(
            status["player2_time"], active == 2, on_break
        )
        self.p1_card.timer_label.setText(format_time(p1_time))
        self.p2_card.timer_label.setText(format_time(p2_time))
        
        # Update break tokens display
        p1_tokens = status["break_tokens_p1"]
        p2_tokens = status["break_tokens_p2"]
        self.p1_card.break_label.setText(f"Break tokens: {p1_tokens}/2")
        self.p2_card.break_label.setText(f"Break tokens: {p2_tokens}/2")
        self.p1_card.break_bar.setValue(p1_tokens)
        self.p2_card.break_bar.setValue(p2_tokens)

        # Calculate and display estimated finish times for both players
        from datetime import datetime, timedelta
        import time as time_module
        
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
            if active == status["active_player"] and not on_break:
                sw += max(0.0, (time.time() - sm.state.last_tick) / 60.0)
            self.stopwatch_label.setText(
                f"⏱ Stopwatch: {format_time(sw)} (overtime → next player bonus)"
            )
            self.stopwatch_label.setStyleSheet("color: #e67e22; font-weight: bold;")
        else:
            self.stopwatch_label.setText("Stopwatch: OFF")
            self.stopwatch_label.setStyleSheet("color: #888;")

        alarm = status.get("alarm_active", False)
        alarm_reason = status.get("alarm_reason", "")
        if alarm:
            if alarm_reason:
                self.alarm_banner.setText(f"⏰ {alarm_reason.upper()} — Dismiss alarm to continue")
            else:
                self.alarm_banner.setText("⏰ TIME UP — Dismiss alarm to continue")
        self.alarm_banner.setVisible(alarm)
        self.dismiss_btn.setVisible(alarm)

        low_style = "color: #e74c3c;"
        for card, time_val, depleted in [
            (self.p1_card, p1_time, status.get("player1_depleted")),
            (self.p2_card, p2_time, status.get("player2_depleted")),
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
        if not QSystemTrayIcon.isSystemTrayAvailable():
            # No tray (e.g. Explorer restart, remote/kiosk session): keep the
            # window usable instead of hiding an app the user can't restore.
            self.tray_icon = None
            self._tray_notified = True  # suppress balloon attempts
            self._minimize_to_tray = False
            return
        self._minimize_to_tray = True

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

        # Build context menu (parented to self so it isn't GC'd)
        tray_menu = QMenu(self)
        open_action = QAction("Open", self)
        open_action.triggered.connect(self._show_window)
        tray_menu.addAction(open_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()
        self._tray_notified = False

    def _tray_activated(self, reason) -> None:
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
        try:
            if self.tray_icon is not None:
                self.tray_icon.hide()
        except RuntimeError:
            pass  # native tray already destroyed (e.g. Explorer restart)
        QApplication.quit()

    def _tray_show_message(self, title: str, msg: str) -> None:
        """Safely show a tray balloon; no-op if tray is gone."""
        try:
            if self.tray_icon is not None:
                self.tray_icon.showMessage(
                    title, msg,
                    QSystemTrayIcon.MessageIcon.Information, 2000,
                )
        except RuntimeError:
            pass  # native tray already destroyed

    def changeEvent(self, event) -> None:
        """Intercept minimize to hide to tray instead of taskbar."""
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized() and self._minimize_to_tray:
                self.hide()
                if not self._tray_notified:
                    self._tray_notified = True
                    self._tray_show_message(
                        "PC Rotation Manager",
                        "Still running — double-click tray icon to reopen. This notification will only show once.",
                    )
        super().changeEvent(event)

    def closeEvent(self, event) -> None:
        """Close button hides to tray instead of quitting.
        When the tray is unavailable the window simply minimizes to the
        taskbar so the app can always be restored."""
        event.ignore()
        if self._minimize_to_tray:
            self.hide()
            if not self._tray_notified:
                self._tray_notified = True
                self._tray_show_message(
                    "PC Rotation Manager",
                    "Minimized to tray — right-click icon and select Quit to exit. This notification will only show once.",
                )
        else:
            self.showMinimized()
