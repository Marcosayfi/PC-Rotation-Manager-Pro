"""User settings dialog for configuring multiple time alerts and preferences."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTime, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from backend.settings import UserSettings, seconds_to_hhmmss
from backend.state_manager import StateManager
from ui.alarm import AlarmPlayer, BUILTIN_ALARM_SOUNDS, SUPPORTED_AUDIO_EXTENSIONS, resolve_alarm_sound_path


class SettingsDialog(QDialog):
    def __init__(self, state_manager: StateManager, parent=None) -> None:
        super().__init__(parent)
        self.state_manager = state_manager
        self.alarm = AlarmPlayer()
        self.settings: UserSettings = self.state_manager.user_settings
        self._custom_sounds = [dict(sound) for sound in self.settings.custom_alarm_sounds]

        self.setWindowTitle("Settings — PC Rotation Manager Pro")
        self.setMinimumWidth(500)
        self.setMinimumHeight(560)
        self.setModal(True)

        self._build_ui()
        self._load_from_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Header
        title = QLabel("Application Settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # 1. Remaining Time Alerts Group
        alert_group = QGroupBox("Remaining Time Alerts (Triggers Full Alarm)")
        alert_layout = QVBoxLayout(alert_group)
        alert_layout.setSpacing(10)

        self.alert_enable_cb = QCheckBox("Enable Remaining Time Alerts")
        self.alert_enable_cb.toggled.connect(self._on_alert_toggled)
        alert_layout.addWidget(self.alert_enable_cb)

        alert_desc = QLabel(
            "When timer reaches any configured alert time, the alarm sound plays and "
            "the banner appears until you click 'Dismiss Alarm'."
        )
        alert_desc.setWordWrap(True)
        alert_desc.setStyleSheet("color: #aaa; font-size: 11px;")
        alert_layout.addWidget(alert_desc)

        # List of configured alert times
        list_row = QHBoxLayout()
        self.alerts_list = QListWidget()
        self.alerts_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.alerts_list.setStyleSheet(
            "QListWidget { background: #222; border: 1px solid #3d3d3d; border-radius: 6px; padding: 4px; font-family: Consolas; font-size: 13px; }"
            "QListWidget::item { padding: 5px 10px; border-radius: 4px; color: #eee; }"
            "QListWidget::item:selected { background: #2e7d32; color: #fff; }"
        )
        list_row.addWidget(self.alerts_list, 1)

        list_btn_vbox = QVBoxLayout()
        self.remove_alert_btn = QPushButton("Remove Selected")
        self.remove_alert_btn.clicked.connect(self._remove_selected_alert)
        self.clear_alerts_btn = QPushButton("Clear All")
        self.clear_alerts_btn.clicked.connect(self.alerts_list.clear)
        list_btn_vbox.addWidget(self.remove_alert_btn)
        list_btn_vbox.addWidget(self.clear_alerts_btn)
        list_btn_vbox.addStretch()
        list_row.addLayout(list_btn_vbox)
        alert_layout.addLayout(list_row)

        # Add new alert input row
        add_frame = QFrame()
        add_frame.setStyleSheet("background: #202020; border: 1px solid #333; border-radius: 6px; padding: 6px;")
        add_layout = QVBoxLayout(add_frame)
        add_layout.setSpacing(6)

        add_input_row = QHBoxLayout()
        add_input_row.addWidget(QLabel("Add Alert Time (HH:mm:ss):"))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        self.time_edit.setTime(QTime(1, 0, 0))
        self.time_edit.setMinimumTime(QTime(0, 0, 5))
        self.time_edit.setMaximumTime(QTime(23, 59, 59))
        self.time_edit.setToolTip("Format: HH:mm:ss (e.g. 01:00:00 = 1 hour remaining)")
        add_input_row.addWidget(self.time_edit)

        self.add_alert_btn = QPushButton("➕ Add Alert")
        self.add_alert_btn.clicked.connect(self._add_alert_from_time_edit)
        self.add_alert_btn.setStyleSheet("background: #2e7d32; color: white; font-weight: bold;")
        add_input_row.addWidget(self.add_alert_btn)
        add_layout.addLayout(add_input_row)

        # Preset shortcut buttons
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Quick Presets:"))
        for label, h, m, s in [
            ("+15m", 0, 15, 0),
            ("+30m", 0, 30, 0),
            ("+45m", 0, 45, 0),
            ("+1 hr", 1, 0, 0),
            ("+1h 30m", 1, 30, 0),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, hr=h, mn=m, sc=s: self._add_alert_seconds(hr * 3600 + mn * 60 + sc))
            preset_row.addWidget(btn)
        add_layout.addLayout(preset_row)
        alert_layout.addWidget(add_frame)

        self.alert_toast_cb = QCheckBox("Show Windows notification when alert triggers")
        alert_layout.addWidget(self.alert_toast_cb)

        layout.addWidget(alert_group)

        # 2. Alarm Sound Group
        sound_group = QGroupBox("Alarm Sound")
        sound_layout = QVBoxLayout(sound_group)
        sound_layout.setSpacing(8)

        self.sounds_list = QListWidget()
        self.sounds_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.sounds_list.itemSelectionChanged.connect(self._on_sound_selection_changed)
        self.sounds_list.setMinimumHeight(86)
        self.sounds_list.setMaximumHeight(130)
        self.sounds_list.setStyleSheet(
            "QListWidget { background: #222; border: 1px solid #3d3d3d; border-radius: 6px; padding: 4px; font-size: 13px; }"
            "QListWidget::item { padding: 6px 8px; border-radius: 4px; color: #eee; }"
            "QListWidget::item:selected { background: #2e7d32; color: #fff; }"
        )
        sound_layout.addWidget(self.sounds_list)

        sound_btn_row = QHBoxLayout()
        self.add_sound_btn = QPushButton("Add Custom Sound")
        self.add_sound_btn.clicked.connect(self._add_custom_sound)
        sound_btn_row.addWidget(self.add_sound_btn)

        self.test_alarm_btn = QPushButton("🔔 Test Selected Sound")
        self.test_alarm_btn.clicked.connect(self._toggle_test_alarm)
        sound_btn_row.addWidget(self.test_alarm_btn)
        sound_btn_row.addStretch()
        sound_layout.addLayout(sound_btn_row)

        layout.addWidget(sound_group)

        # 3. Time Up Group
        timeup_group = QGroupBox("Time Up (00:00:00) Settings")
        timeup_layout = QVBoxLayout(timeup_group)
        timeup_layout.setSpacing(6)

        self.timeup_toast_cb = QCheckBox("Show Windows notification when player time reaches zero")
        timeup_layout.addWidget(self.timeup_toast_cb)
        layout.addWidget(timeup_group)

        # Storage info notice
        info_label = QLabel(
            f"Settings saved in: {self.state_manager.settings_manager.settings_path}"
        )
        info_label.setStyleSheet("color: #888; font-size: 11px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Dialog buttons
        btn_box = QHBoxLayout()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_box.addWidget(reset_btn)
        btn_box.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_close)
        save_btn.setStyleSheet("background: #4caf50; color: white; padding: 6px 18px; font-weight: bold;")
        btn_box.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        layout.addLayout(btn_box)

        self.setStyleSheet(
            "QDialog { background: #181818; color: #eee; }"
            "QGroupBox { border: 1px solid #333; border-radius: 8px; margin-top: 10px; padding-top: 14px; font-weight: bold; color: #4caf50; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }"
            "QLabel { color: #ddd; }"
            "QCheckBox { color: #eee; spacing: 8px; }"
            "QTimeEdit { background: #252525; border: 1px solid #444; border-radius: 4px; color: #fff; padding: 4px; font-size: 13px; font-family: Consolas; }"
            "QPushButton { background: #2a2a2a; border: 1px solid #444; border-radius: 4px; color: #eee; padding: 5px 12px; }"
            "QPushButton:hover { background: #3a3a3a; border-color: #666; }"
        )

    def _on_alert_toggled(self, enabled: bool) -> None:
        self.alerts_list.setEnabled(enabled)
        self.time_edit.setEnabled(enabled)
        self.add_alert_btn.setEnabled(enabled)
        self.remove_alert_btn.setEnabled(enabled)
        self.clear_alerts_btn.setEnabled(enabled)
        self.alert_toast_cb.setEnabled(enabled)

    def _load_sound_list(self, selected_id: str) -> None:
        self.sounds_list.clear()
        selected_row = 0
        for sound in BUILTIN_ALARM_SOUNDS:
            row = self.sounds_list.count()
            self._add_sound_item(sound, custom=False)
            if sound["id"] == selected_id:
                selected_row = row

        for sound in self._custom_sounds:
            row = self.sounds_list.count()
            self._add_sound_item(sound, custom=True)
            if sound["id"] == selected_id:
                selected_row = row

        if self.sounds_list.count():
            self.sounds_list.setCurrentRow(selected_row)

    def _add_sound_item(self, sound: dict[str, str], custom: bool) -> None:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, {**sound, "custom": custom})
        self.sounds_list.addItem(item)

        if not custom:
            item.setText(sound["name"])
            return

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(8, 2, 4, 2)
        row_layout.setSpacing(6)

        label = QLabel(f"{sound['name']} - Custom")
        label.setStyleSheet("color: #eee;")
        row_layout.addWidget(label, 1)

        delete_btn = QPushButton("🗑")
        delete_btn.setFixedWidth(32)
        delete_btn.setToolTip("Remove custom sound")
        delete_btn.clicked.connect(lambda _, sound_id=sound["id"]: self._delete_custom_sound(sound_id))
        row_layout.addWidget(delete_btn)

        item.setSizeHint(row_widget.sizeHint())
        self.sounds_list.setItemWidget(item, row_widget)

    def _selected_sound(self) -> dict[str, str] | None:
        item = self.sounds_list.currentItem()
        if not item:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            return data
        return None

    def _add_custom_sound(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Add Custom Alarm Sound",
            str(Path.home()),
            "Audio files (*.wav *.mp3 *.ogg);;WAV audio (*.wav);;MP3 audio (*.mp3);;Ogg audio (*.ogg)",
        )
        if not file_path:
            return

        path = Path(file_path)
        if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            QMessageBox.warning(self, "Unsupported Sound", "Custom alarm sounds must be WAV, MP3, or OGG files.")
            return
        if not path.exists():
            QMessageBox.warning(self, "Missing Sound", "That sound file could not be found.")
            return

        resolved_path = str(path.resolve())
        for sound in self._custom_sounds:
            if sound["path"] == resolved_path:
                self._load_sound_list(sound["id"])
                return

        sound = {
            "id": f"custom:{resolved_path}",
            "name": path.stem,
            "path": resolved_path,
        }
        self._custom_sounds.append(sound)
        self._load_sound_list(sound["id"])

    def _delete_custom_sound(self, sound_id: str) -> None:
        selected = self._selected_sound()
        selected_id = selected["id"] if selected else "time_up"
        self._custom_sounds = [sound for sound in self._custom_sounds if sound["id"] != sound_id]
        if selected_id == sound_id:
            selected_id = "time_up"
        if self.alarm.is_playing:
            self.alarm.stop()
            self.test_alarm_btn.setText("🔔 Test Selected Sound")
        self._load_sound_list(selected_id)

    def _on_sound_selection_changed(self) -> None:
        if self.alarm.is_playing:
            self.alarm.stop()
            self.test_alarm_btn.setText("🔔 Test Selected Sound")

    def _load_from_settings(self) -> None:
        s = self.settings
        self.alert_enable_cb.setChecked(s.time_alert_enabled)
        self.alerts_list.clear()
        for sec in sorted(s.time_alerts, reverse=True):
            self._add_alert_item(sec)
        self.alert_toast_cb.setChecked(s.time_alert_toast_enabled)
        self.timeup_toast_cb.setChecked(s.time_up_toast_enabled)
        self._load_sound_list(s.alarm_sound_id)
        self._on_alert_toggled(s.time_alert_enabled)

    def _add_alert_item(self, seconds: int) -> None:
        time_str = seconds_to_hhmmss(seconds)
        # Check if duplicate exists
        for i in range(self.alerts_list.count()):
            if self.alerts_list.item(i).data(Qt.ItemDataRole.UserRole) == seconds:
                return
        item = QListWidgetItem(f"⏰ Alert at {time_str} remaining ({seconds // 60} min)")
        item.setData(Qt.ItemDataRole.UserRole, seconds)
        self.alerts_list.addItem(item)

    def _add_alert_seconds(self, seconds: int) -> None:
        self._add_alert_item(seconds)

    def _add_alert_from_time_edit(self) -> None:
        qtime = self.time_edit.time()
        sec = qtime.hour() * 3600 + qtime.minute() * 60 + qtime.second()
        if sec <= 0:
            return
        self._add_alert_item(sec)

    def _remove_selected_alert(self) -> None:
        row = self.alerts_list.currentRow()
        if row >= 0:
            self.alerts_list.takeItem(row)

    def _toggle_test_alarm(self) -> None:
        """Toggle test alarm sound."""
        if self.alarm.is_playing:
            self.alarm.stop()
            self.test_alarm_btn.setText("🔔 Test Selected Sound")
        else:
            selected = self._selected_sound()
            sound_id = selected["id"] if selected else "time_up"
            self.alarm.start(resolve_alarm_sound_path(sound_id, self._custom_sounds))
            self.test_alarm_btn.setText("⏹ Stop Test Alarm")

    def closeEvent(self, event) -> None:
        self.alarm.stop()
        super().closeEvent(event)

    def reject(self) -> None:
        self.alarm.stop()
        super().reject()

    def accept(self) -> None:
        self.alarm.stop()
        super().accept()

    def _reset_defaults(self) -> None:
        defaults = UserSettings()
        self.alert_enable_cb.setChecked(defaults.time_alert_enabled)
        self.alerts_list.clear()
        for sec in sorted(defaults.time_alerts, reverse=True):
            self._add_alert_item(sec)
        self.time_edit.setTime(QTime(1, 0, 0))
        self.alert_toast_cb.setChecked(defaults.time_alert_toast_enabled)
        self.timeup_toast_cb.setChecked(defaults.time_up_toast_enabled)
        self._custom_sounds = []
        self._load_sound_list(defaults.alarm_sound_id)
        self._on_alert_toggled(defaults.time_alert_enabled)

    def _save_and_close(self) -> None:
        alert_seconds_list: list[int] = []
        for i in range(self.alerts_list.count()):
            val = self.alerts_list.item(i).data(Qt.ItemDataRole.UserRole)
            if isinstance(val, int) and val > 0:
                alert_seconds_list.append(val)

        new_settings = UserSettings(
            time_alert_enabled=self.alert_enable_cb.isChecked(),
            time_alerts=sorted(list(set(alert_seconds_list))),
            time_alert_toast_enabled=self.alert_toast_cb.isChecked(),
            time_up_toast_enabled=self.timeup_toast_cb.isChecked(),
            alarm_sound_id=(self._selected_sound() or {"id": "time_up"})["id"],
            custom_alarm_sounds=self._custom_sounds,
        )

        ok = self.state_manager.settings_manager.save(new_settings)
        if ok:
            self.state_manager.reload_user_settings()
            self.accept()
        else:
            QMessageBox.warning(self, "Save Error", "Could not write settings to Local AppData.")
