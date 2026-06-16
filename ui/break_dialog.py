"""Break reason selection dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QMessageBox,
)


class BreakDialog(QDialog):
    REASONS = ["toilet", "eat", "rest"]

    def __init__(self, parent=None, state_manager=None) -> None:
        super().__init__(parent)
        self.state_manager = state_manager
        self.setWindowTitle("Start Break")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Why are you having a break?"))
        layout.addWidget(QLabel("Max 3 break tokens per session."))

        self._group = QButtonGroup(self)
        for reason in self.REASONS:
            rb = QRadioButton(reason.capitalize())
            rb.setProperty("reason", reason)
            self._group.addButton(rb)
            layout.addWidget(rb)

        self._other_rb = QRadioButton("Other")
        self._group.addButton(self._other_rb)
        layout.addWidget(self._other_rb)

        other_row = QHBoxLayout()
        other_row.addWidget(QLabel("Details:"))
        self._other_input = QLineEdit()
        self._other_input.setPlaceholderText("Describe your break…")
        self._other_input.setEnabled(False)
        other_row.addWidget(self._other_input)
        layout.addLayout(other_row)

        self._other_rb.toggled.connect(self._other_input.setEnabled)

        # Unfair break option
        layout.addWidget(QLabel(""))
        self._unfair_rb = QRadioButton("⚠️ Unfair Break (no token cost, requires both secret codes)")
        self._group.addButton(self._unfair_rb)
        layout.addWidget(self._unfair_rb)

        unfair_row = QHBoxLayout()
        unfair_row.addWidget(QLabel("P1 Secret:"))
        self._p1_secret_input = QLineEdit()
        self._p1_secret_input.setPlaceholderText("Player 1 secret code")
        self._p1_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._p1_secret_input.setEnabled(False)
        unfair_row.addWidget(self._p1_secret_input)
        layout.addLayout(unfair_row)

        unfair_row2 = QHBoxLayout()
        unfair_row2.addWidget(QLabel("P2 Secret:"))
        self._p2_secret_input = QLineEdit()
        self._p2_secret_input.setPlaceholderText("Player 2 secret code")
        self._p2_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._p2_secret_input.setEnabled(False)
        unfair_row2.addWidget(self._p2_secret_input)
        layout.addLayout(unfair_row2)

        self._unfair_rb.toggled.connect(self._on_unfair_toggled)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._reason: str | None = None
        self._is_unfair: bool = False

    def _on_unfair_toggled(self, checked: bool) -> None:
        self._p1_secret_input.setEnabled(checked)
        self._p2_secret_input.setEnabled(checked)

    def _on_accept(self) -> None:
        checked = self._group.checkedButton()
        if not checked:
            return

        if checked is self._unfair_rb:
            p1_secret = self._p1_secret_input.text().strip()
            p2_secret = self._p2_secret_input.text().strip()
            if not p1_secret or not p2_secret:
                QMessageBox.warning(self, "Error", "Both secret codes are required for unfair break.")
                return
            self._is_unfair = True
            self._reason = f"unfair_break"
        elif checked is self._other_rb:
            text = self._other_input.text().strip()
            if not text:
                self._other_input.setStyleSheet("border: 2px solid #e74c3c;")
                return
            self._reason = f"other: {text}"
            self._is_unfair = False
        else:
            self._reason = checked.property("reason")
            self._is_unfair = False
        self.accept()

    def get_reason(self) -> str | None:
        return self._reason
    
    def is_unfair(self) -> bool:
        return self._is_unfair
    
    def get_secret_codes(self) -> tuple[str, str] | None:
        if self._is_unfair:
            return (self._p1_secret_input.text().strip(), self._p2_secret_input.text().strip())
        return None

