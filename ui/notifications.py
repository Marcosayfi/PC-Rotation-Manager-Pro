"""Windows 10+ notification support."""

from __future__ import annotations

from pathlib import Path


def send_windows_notification(title: str, message: str) -> None:
    """Send a Windows 10+ notification.
    
    Requires Windows 10 or later. Uses the built-in toast notification system.
    """
    try:
        from win10toast import ToastNotifier
        
        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            message,
            duration=10,
            threaded=True,
        )
    except ImportError:
        # Fallback: just print if win10toast is not installed
        print(f"[Notification] {title}: {message}")
    except Exception as e:
        print(f"Failed to send notification: {e}")


def send_alarm_notification(player: int) -> None:
    """Send an alarm notification when a player's time reaches 0."""
    send_windows_notification(
        "⏰ PC Rotation Manager — TIME UP!",
        f"Player {player}'s time has ended. Click to return.",
    )
