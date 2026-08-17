"""Windows 10+ notification support."""

from __future__ import annotations

import sys
import threading


def send_windows_notification(title: str, message: str) -> None:
    """Send a Windows 10+ notification.
    
    Requires Windows 10 or later. Uses the built-in toast notification system.
    """
    def _do_notify():
        try:
            from win10toast import ToastNotifier

            toaster = ToastNotifier()
            toaster.show_toast(
                title,
                message,
                duration=10,
                threaded=True,
            )
        except BaseException:
            try:
                # Safe stdout write without charmap encoding crashes
                clean_title = title.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
                clean_msg = message.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
                print(f"[Notification] {clean_title}: {clean_msg}")
            except BaseException:
                pass

    threading.Thread(target=_do_notify, daemon=True, name="toast_notifier").start()


def send_alarm_notification(player: int) -> None:
    """Send an alarm notification when a player's time reaches 0."""
    send_windows_notification(
        "⏰ PC Rotation Manager — TIME UP!",
        f"Player {player}'s time has ended. Click to return.",
    )


def send_time_alert_notification(player: int, remaining_str: str) -> None:
    """Send a time alert notification when player reaches configured alert threshold."""
    send_windows_notification(
        "⏰ PC Rotation Manager — Time Alert",
        f"Player {player} has {remaining_str} remaining!",
    )
