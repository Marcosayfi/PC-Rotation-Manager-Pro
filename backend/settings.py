"""User settings and local configuration persistence."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def get_user_settings_dir() -> Path:
    """Return %LOCALAPPDATA%/PCRotationManagerPro path."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / "AppData" / "Local"
    app_dir = base / "PCRotationManagerPro"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def seconds_to_hhmmss(total_seconds: int) -> str:
    """Convert total seconds to HH:MM:SS format."""
    total_seconds = max(0, int(total_seconds))
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def hhmmss_to_seconds(hhmmss: str) -> int:
    """Convert HH:MM:SS string to total seconds."""
    parts = hhmmss.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + int(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + int(s)
    elif len(parts) == 1:
        return int(parts[0])
    return 3600


@dataclass
class UserSettings:
    time_alert_enabled: bool = True
    time_alerts: list[int] = field(default_factory=lambda: [3600])  # List of alert thresholds in seconds
    time_alert_toast_enabled: bool = True
    time_up_toast_enabled: bool = True
    alarm_sound_id: str = "time_up"
    custom_alarm_sounds: list[dict[str, str]] = field(default_factory=list)


class SettingsManager:
    def __init__(self, settings_path: Path | None = None) -> None:
        if settings_path is None:
            self.settings_path = get_user_settings_dir() / "settings.json"
        else:
            self.settings_path = settings_path

    def load(self) -> UserSettings:
        """Load user settings from AppData/Local JSON file."""
        if not self.settings_path.exists():
            default = UserSettings()
            self.save(default)
            return default

        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Backwards compatibility: migrate single time_alert_seconds to list
            if "time_alert_seconds" in data and "time_alerts" not in data:
                data["time_alerts"] = [data["time_alert_seconds"]]
            fields = UserSettings.__dataclass_fields__
            filtered = {k: v for k, v in data.items() if k in fields}
            settings = UserSettings(**filtered)
            settings.custom_alarm_sounds = self._normalize_custom_sounds(settings.custom_alarm_sounds)
            valid_sound_ids = {"time_up", "chime", *(sound["id"] for sound in settings.custom_alarm_sounds)}
            if settings.alarm_sound_id not in valid_sound_ids:
                settings.alarm_sound_id = "time_up"
            return settings
        except (json.JSONDecodeError, OSError, TypeError):
            return UserSettings()

    def _normalize_custom_sounds(self, sounds: object) -> list[dict[str, str]]:
        if not isinstance(sounds, list):
            return []

        normalized: list[dict[str, str]] = []
        seen: set[str] = set()
        for sound in sounds:
            if not isinstance(sound, dict):
                continue
            path = str(sound.get("path", "")).strip()
            if not path or path in seen:
                continue
            name = str(sound.get("name", "")).strip() or Path(path).stem
            sound_id = str(sound.get("id", "")).strip() or f"custom:{path}"
            normalized.append({"id": sound_id, "name": name, "path": path})
            seen.add(path)
        return normalized

    def save(self, settings: UserSettings) -> bool:
        """Atomically save user settings to AppData/Local JSON file."""
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.settings_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(asdict(settings), f, indent=2)
            tmp.replace(self.settings_path)
            return True
        except OSError:
            return False
