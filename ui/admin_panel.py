"""Hidden admin panel (Ctrl+Shift+A)."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from backend.state_manager import BASE_TIME_MINUTES, StateManager


class AdminPanel(QDialog):
    def __init__(self, state_manager: StateManager, parent=None) -> None:
        super().__init__(parent)
        self.state_manager = state_manager
        self.setWindowTitle("Admin Panel — PC Rotation Manager Pro")
        self.setMinimumSize(520, 480)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Timers tab
        timers = QWidget()
        form = QFormLayout(timers)
        self.p1_spin = QDoubleSpinBox()
        self.p1_spin.setRange(0, 999)
        self.p1_spin.setSuffix(" min")
        self.p2_spin = QDoubleSpinBox()
        self.p2_spin.setRange(0, 999)
        self.p2_spin.setSuffix(" min")
        form.addRow("Player 1 time:", self.p1_spin)
        form.addRow("Player 2 time:", self.p2_spin)
        apply_btn = QPushButton("Apply Times")
        apply_btn.clicked.connect(self._apply_times)
        form.addRow(apply_btn)
        tabs.addTab(timers, "Edit Times")

        # Security tab
        security = QWidget()
        sec_form = QFormLayout(security)
        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText("Leave empty for read-only mobile API")
        sec_form.addRow("Admin API token:", self.token_edit)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        sec_form.addRow("Server port:", self.port_spin)
        save_cfg = QPushButton("Save Network Settings")
        save_cfg.clicked.connect(self._save_network)
        sec_form.addRow(save_cfg)
        tabs.addTab(security, "Network")

        # Secrets tab (for unfair break & admin protection)
        secrets_w = QWidget()
        secrets_form = QFormLayout(secrets_w)
        secrets_form.addRow(QLabel("Secret codes (both required for unfair breaks & admin lock):"))
        
        self.p1_secret_edit = QLineEdit()
        self.p1_secret_edit.setPlaceholderText("Player 1 secret code (plaintext, will be base64 encoded)")
        self.p1_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        secrets_form.addRow("Player 1 secret:", self.p1_secret_edit)
        
        self.p2_secret_edit = QLineEdit()
        self.p2_secret_edit.setPlaceholderText("Player 2 secret code (plaintext, will be base64 encoded)")
        self.p2_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        secrets_form.addRow("Player 2 secret:", self.p2_secret_edit)
        
        save_secrets_btn = QPushButton("Save Secret Codes")
        save_secrets_btn.clicked.connect(self._save_secrets)
        secrets_form.addRow(save_secrets_btn)
        
        secrets_form.addRow(QLabel(""))
        secrets_form.addRow(QLabel("Status:"))
        self.p1_secret_status = QLabel("Not set")
        self.p2_secret_status = QLabel("Not set")
        secrets_form.addRow("P1:", self.p1_secret_status)
        secrets_form.addRow("P2:", self.p2_secret_status)
        tabs.addTab(secrets_w, "Secret Codes")

        # Actions tab
        actions = QWidget()
        act_layout = QVBoxLayout(actions)
        act_layout.addWidget(QLabel("Administrative actions:"))

        reset_btn = QPushButton("Reset All Timers (125 min each)")
        reset_btn.clicked.connect(self._reset_all)
        act_layout.addWidget(reset_btn)

        force_btn = QPushButton("Force Switch Player")
        force_btn.clicked.connect(self._force_switch)
        act_layout.addWidget(force_btn)

        restart_btn = QPushButton("Restart System State")
        restart_btn.clicked.connect(self._restart_state)
        act_layout.addWidget(restart_btn)

        dismiss_btn = QPushButton("Dismiss Active Alarm")
        dismiss_btn.clicked.connect(self._dismiss_alarm)
        act_layout.addWidget(dismiss_btn)
        act_layout.addStretch()
        tabs.addTab(actions, "Actions")

        # Logs tab
        logs_w = QWidget()
        logs_layout = QVBoxLayout(logs_w)
        self.logs_view = QTextEdit()
        self.logs_view.setReadOnly(True)
        logs_layout.addWidget(self.logs_view)
        refresh_logs = QPushButton("Refresh Logs")
        refresh_logs.clicked.connect(self._refresh_logs)
        logs_layout.addWidget(refresh_logs)
        tabs.addTab(logs_w, "Full Logs")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._load_values()

    def _load_values(self) -> None:
        try:
            status = self.state_manager.get_status()
            self.p1_spin.setValue(status["player1_time"])
            self.p2_spin.setValue(status["player2_time"])
            self.token_edit.setText(self.state_manager.admin_token or "")
            self.port_spin.setValue(self.state_manager.server_port)
            
            # Update secret code status (safe check)
            if hasattr(self, 'p1_secret_status') and hasattr(self, 'p2_secret_status'):
                p1_secret = self.state_manager.get_secret_code(1)
                p2_secret = self.state_manager.get_secret_code(2)
                self.p1_secret_status.setText("✓ Set" if p1_secret else "✗ Not set")
                self.p1_secret_status.setStyleSheet("color: #4caf50;" if p1_secret else "color: #e74c3c;")
                self.p2_secret_status.setText("✓ Set" if p2_secret else "✗ Not set")
                self.p2_secret_status.setStyleSheet("color: #4caf50;" if p2_secret else "color: #e74c3c;")
            
            self._refresh_logs()
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Values", f"Failed to load admin panel values:\n{e}")

    def _apply_times(self) -> None:
        self.state_manager.set_player_times(self.p1_spin.value(), self.p2_spin.value())
        QMessageBox.information(self, "Saved", "Player times updated.")

    def _save_network(self) -> None:
        token = self.token_edit.text().strip() or None
        self.state_manager.set_admin_token(token)
        self.state_manager.save_network_settings(self.port_spin.value())
        QMessageBox.information(
            self,
            "Saved",
            "Network settings saved. Restart the app for port changes to take effect.",
        )

    def _save_secrets(self) -> None:
        p1 = self.p1_secret_edit.text().strip()
        p2 = self.p2_secret_edit.text().strip()
        
        if not p1 or not p2:
            QMessageBox.warning(self, "Error", "Both secret codes must be filled in.")
            return
        
        import base64
        try:
            p1_encoded = base64.b64encode(p1.encode("utf-8")).decode("utf-8")
            p2_encoded = base64.b64encode(p2.encode("utf-8")).decode("utf-8")
            self.state_manager.set_secret_code(1, p1_encoded)
            self.state_manager.set_secret_code(2, p2_encoded)
            self.p1_secret_edit.clear()
            self.p2_secret_edit.clear()
            self._load_values()
            QMessageBox.information(self, "Saved", "Secret codes saved securely.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save secrets: {e}")

    def _reset_all(self) -> None:
        if QMessageBox.question(self, "Confirm", "Reset all timers to 125 minutes?") != QMessageBox.StandardButton.Yes:
            return
        self.state_manager.reset_all()
        self.p1_spin.setValue(BASE_TIME_MINUTES)
        self.p2_spin.setValue(BASE_TIME_MINUTES)
        QMessageBox.information(self, "Done", "All timers reset.")

    def _force_switch(self) -> None:
        ok, msg = self.state_manager.switch_player(force=True)
        if ok:
            QMessageBox.information(self, "Done", msg)
        else:
            QMessageBox.warning(self, "Failed", msg)

    def _restart_state(self) -> None:
        if QMessageBox.question(self, "Confirm", "Clear all state and restart fresh?") != QMessageBox.StandardButton.Yes:
            return
        self.state_manager.restart_system_state()
        self._load_values()
        QMessageBox.information(self, "Done", "System state restarted.")

    def _dismiss_alarm(self) -> None:
        self.state_manager.dismiss_alarm()

    def _refresh_logs(self) -> None:
        lines = self.state_manager.logger.get_all()
        self.logs_view.setPlainText("\n".join(lines))
