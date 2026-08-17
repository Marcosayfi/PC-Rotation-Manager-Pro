"""Core state, timer logic, and persistence."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from backend.logger import ActionLogger
from backend.settings import SettingsManager, UserSettings, seconds_to_hhmmss

BASE_TIME_MINUTES = 125.0
MAX_BREAK_TOKENS = 2
AUTOSAVE_INTERVAL_SEC = 7.0


@dataclass
class AppState:
    player1_time: float = BASE_TIME_MINUTES
    player2_time: float = BASE_TIME_MINUTES
    active_player: int = 1
    stopwatch_mode: bool = False
    stopwatch_minutes: float = 0.0
    stopwatch_started_at: float | None = None
    break_tokens_p1: int = MAX_BREAK_TOKENS
    break_tokens_p2: int = MAX_BREAK_TOKENS
    on_break: bool = False
    break_player: int | None = None
    break_reason: str = ""
    break_started_at: float | None = None
    session_started_at: float = field(default_factory=time.time)
    alarm_active: bool = False
    alarm_dismissed: bool = False
    alarm_reason: str = ""
    last_tick: float = field(default_factory=time.time)
    player1_depleted: bool = False
    player2_depleted: bool = False
    unfair_break_approved: bool = False

    def to_api_dict(self) -> dict:
        return {
            "player1_time": round(max(0.0, self.player1_time), 5),
            "player2_time": round(max(0.0, self.player2_time), 5),
            "active_player": self.active_player,
            "stopwatch_mode": self.stopwatch_mode,
            "stopwatch_minutes": round(self.stopwatch_minutes, 5),
            "break_tokens_p1": self.break_tokens_p1,
            "break_tokens_p2": self.break_tokens_p2,
            "on_break": self.on_break,
            "break_player": self.break_player,
            "break_reason": self.break_reason,
            "alarm_active": self.alarm_active,
            "alarm_reason": self.alarm_reason,
            "player1_depleted": self.player1_depleted,
            "player2_depleted": self.player2_depleted,
            "unfair_break_approved": self.unfair_break_approved,
        }


class StateManager:
    def _ensure_shared_access(self) -> None:
        """Grant the Users group write permission on the data directory so that
        all standard users can read and write state.  Only applies on Windows.
        Silently ignores failures (non-admin users cannot change ACLs)."""
        if sys.platform != "win32":
            return
        try:
            subprocess.run(
                [
                    "icacls",
                    str(self.data_dir),
                    "/grant", "Users:(OI)(CI)M",
                    "/q",
                ],
                capture_output=True,
                timeout=10,
            )
        except Exception:
            pass

    def __init__(
        self,
        data_dir: Path,
        on_alarm: Callable[[], None] | None = None,
        on_alarm_clear: Callable[[], None] | None = None,
        on_state_change: Callable[[], None] | None = None,
        on_time_alert: Callable[[int, int], None] | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_shared_access()
        self.state_path = self.data_dir / "state.json"
        self.config_path = self.data_dir / "config.json"
        self.secrets_path = self.data_dir / "secrets.json"
        self.logger = ActionLogger(self.data_dir / "actions.log")

        self.settings_manager = SettingsManager()
        self.user_settings: UserSettings = self.settings_manager.load()
        # Track triggered threshold per player: player_id -> set of triggered seconds
        self._triggered_alerts: dict[int, set[int]] = {1: set(), 2: set()}

        self.on_alarm = on_alarm
        self.on_alarm_clear = on_alarm_clear
        self.on_state_change = on_state_change
        self.on_time_alert = on_time_alert

        self._lock = threading.RLock()
        self._running = False
        self._tick_thread: threading.Thread | None = None
        self._save_thread: threading.Thread | None = None

        self.admin_token: str | None = None
        self.discord_bot_token: str | None = None
        self.discord_guild_id: str | None = None
        self.server_host = "0.0.0.0"
        self.server_port = 6969
        # Placeholder LAN IP — user must set their real one in config.json
        # (or run fix_ip.ps1). Redacted from the repo for privacy.
        self.advertised_ip = "192.168.1.100"
        self._player1_secret: str | None = None
        self._player2_secret: str | None = None
        self._secrets_prompted = False

        self._load_config()
        self._load_secrets()
        self.state = self._load_state()
        self._check_depleted_on_load()

    def reload_user_settings(self) -> UserSettings:
        """Reload user settings from disk and update in-memory settings."""
        with self._lock:
            self.user_settings = self.settings_manager.load()
            # Clean up triggered alerts that are now below current remaining time
            for p in (1, 2):
                p_time_sec = getattr(self.state, f"player{p}_time") * 60.0
                self._triggered_alerts[p] = {sec for sec in self._triggered_alerts[p] if p_time_sec <= sec}
            return self.user_settings

    def _load_config(self) -> None:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.server_port = int(cfg.get("server_port", 6969))
                self.advertised_ip = cfg.get("advertised_ip", "192.168.1.100")
                token = cfg.get("admin_token")
                self.admin_token = token if token else None
                bot_token = cfg.get("discord_bot_token")
                self.discord_bot_token = bot_token if bot_token else None
                guild_id = cfg.get("discord_guild_id")
                self.discord_guild_id = str(guild_id) if guild_id else None
            except (json.JSONDecodeError, OSError, ValueError):
                pass
        else:
            self._save_config()

    def _save_config(self) -> None:
        cfg = {
            "server_port": self.server_port,
            "advertised_ip": self.advertised_ip,
            "admin_token": self.admin_token,
            "discord_bot_token": self.discord_bot_token,
            "discord_guild_id": self.discord_guild_id,
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except PermissionError:
            self.logger.log(
                "WARNING: Could not write config file — permission denied."
            )
        except OSError as e:
            self.logger.log(f"WARNING: Could not write config file — {e}")

    def _load_secrets(self) -> None:
        if self.secrets_path.exists():
            try:
                with open(self.secrets_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._player1_secret = data.get("player1_secret")
                self._player2_secret = data.get("player2_secret")
            except (json.JSONDecodeError, OSError):
                pass

    def _save_secrets(self) -> None:
        data = {
            "player1_secret": self._player1_secret,
            "player2_secret": self._player2_secret,
        }
        try:
            with open(self.secrets_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except PermissionError:
            self.logger.log(
                "WARNING: Could not write secrets file — permission denied."
            )
        except OSError as e:
            self.logger.log(f"WARNING: Could not write secrets file — {e}")

    def get_secret_code(self, player: int) -> str | None:
        """Get the base64-encoded secret for a player."""
        if player == 1:
            return self._player1_secret
        elif player == 2:
            return self._player2_secret
        return None

    def set_secret_code(self, player: int, code: str) -> None:
        """Store a base64-encoded secret code for a player."""
        if player == 1:
            self._player1_secret = code
        elif player == 2:
            self._player2_secret = code
        self._save_secrets()
        self.logger.log(f"Secret code set for Player {player}")

    def verify_secret_code(self, player: int, code: str) -> bool:
        """Verify if the provided code matches the stored secret."""
        stored = self.get_secret_code(player)
        if not stored:
            return False
        try:
            return base64.b64decode(stored).decode("utf-8") == code
        except Exception:
            return False

    def verify_both_secrets(self, code1: str, code2: str) -> bool:
        """Verify both Player 1 and Player 2 secret codes."""
        return self.verify_secret_code(1, code1) and self.verify_secret_code(2, code2)

    def _load_state(self) -> AppState:
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                now = time.time()
                if raw.get("session_started_at") is None:
                    raw["session_started_at"] = now
                if raw.get("last_tick") is None:
                    raw["last_tick"] = now
                fields = AppState.__dataclass_fields__
                state = AppState(**{k: v for k, v in raw.items() if k in fields})
                state.last_tick = now
                return state
            except (json.JSONDecodeError, OSError, TypeError):
                self.logger.log("Recovered from corrupt state file — using defaults")
        state = AppState()
        self.logger.log("Player 1 started session")
        return state

    def save_state(self) -> None:
        with self._lock:
            data = asdict(self.state)
            
        tmp = self.state_path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp.replace(self.state_path)
        except PermissionError:
            self.logger.log(
                "WARNING: Could not write state file — permission denied. "
                "State is preserved in memory only."
            )
        except OSError as e:
            self.logger.log(f"WARNING: Could not write state file — {e}")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tick_thread = threading.Thread(
            target=self._tick_loop, daemon=True, name="tick"
        )
        self._save_thread = threading.Thread(
            target=self._autosave_loop, daemon=True, name="autosave"
        )
        self._tick_thread.start()
        self._save_thread.start()

    def stop(self) -> None:
        self._running = False
        self.save_state()

    def get_status(self) -> dict:
        # Lock-free read — Python GIL protects individual attribute access.
        # The tick loop holds the lock so briefly (< 1 µs) that contention
        # here is negligible, and reading one cycle stale is harmless.
        return self.state.to_api_dict()

    def _notify(self) -> None:
        if self.on_state_change:
            self.on_state_change()

    def _active_time_key(self) -> str:
        return "player1_time" if self.state.active_player == 1 else "player2_time"

    def _player_name(self, player: int) -> str:
        return f"Player {player}"

    def _apply_elapsed(self, elapsed_minutes: float) -> None:
        should_alarm = False
        alarm_reason_text = ""
        with self._lock:
            if elapsed_minutes <= 0:
                return

            if self.state.on_break:
                # Break doesn't consume timer time, tokens are consumed on start
                return

            if self.state.stopwatch_mode:
                # Stopwatch accumulates for whichever player is currently active
                self.state.stopwatch_minutes += elapsed_minutes

            key = self._active_time_key()
            active_p = self.state.active_player
            current = getattr(self.state, key)
            new_val = max(0.0, current - elapsed_minutes)
            setattr(self.state, key, new_val)

            # Check multiple time alerts (e.g. 01:00:00, 00:30:00, 00:15:00 remaining)
            if self.user_settings.time_alert_enabled and not self.state.alarm_active:
                current_sec = current * 60.0
                new_sec = new_val * 60.0
                for threshold in self.user_settings.time_alerts:
                    if 0 < new_sec <= threshold < current_sec and threshold not in self._triggered_alerts[active_p]:
                        self._triggered_alerts[active_p].add(threshold)
                        should_alarm = True
                        alarm_reason_text = f"Player {active_p} — {seconds_to_hhmmss(threshold)} Remaining Alert"
                        break

            if new_val <= 0 and current > 0:
                depleted_key = f"player{self.state.active_player}_depleted"
                setattr(self.state, depleted_key, True)
                # Enable stopwatch when either player's timer reaches 0
                if not self.state.stopwatch_mode:
                    self.state.stopwatch_mode = True
                    self.state.stopwatch_started_at = time.time()
                if not self.state.alarm_active:
                    should_alarm = True
                    alarm_reason_text = f"Player {self.state.active_player} — Time Up!"

        # Fire alarm outside the lock to avoid blocking it during callbacks.
        if should_alarm:
            self._trigger_alarm(alarm_reason_text)

    def _check_depleted_on_load(self) -> None:
        active_key = self._active_time_key()
        if getattr(self.state, active_key) <= 0:
            self.state.alarm_active = True
            self.state.alarm_reason = f"Player {self.state.active_player} — Time Up!"

    def _trigger_alarm(self, reason: str = "") -> None:
        if self.state.alarm_active:
            return
        self.state.alarm_active = True
        self.state.alarm_dismissed = False
        self.state.alarm_reason = reason
        player = self._player_name(self.state.active_player)
        if not reason:
            reason = f"Timer ended — {player} time reached zero"
        self.logger.log(f"Alarm triggered: {reason}")
        if self.on_alarm:
            self.on_alarm()

    def dismiss_alarm(self) -> None:
        with self._lock:
            if not self.state.alarm_active:
                return
            self.state.alarm_active = False
            self.state.alarm_dismissed = True
            self.logger.log("Alarm dismissed")
            if self.on_alarm_clear:
                self.on_alarm_clear()
            self.save_state()
            self._notify()

    def _tick_loop(self) -> None:
        """Background timer — keeps counting even when the window is hidden."""
        while self._running:
            time.sleep(1.0)
            now = time.time()
            with self._lock:
                elapsed_sec = now - self.state.last_tick
                self.state.last_tick = now
            # Cap jumps after sleep/resume or a stalled thread
            if elapsed_sec > 1.5:
                elapsed_sec = 1.5
            if elapsed_sec > 0:
                self._apply_elapsed(elapsed_sec / 60.0)

    def _autosave_loop(self) -> None:
        while self._running:
            time.sleep(AUTOSAVE_INTERVAL_SEC)
            try:
                self.save_state()
            except OSError:
                pass

    def switch_player(self, force: bool = False) -> tuple[bool, str]:
        with self._lock:
            if self.state.on_break and not force:
                return False, "End the current break before switching players."

            # If stopwatch is running, add accrued overtime to the incoming player
            if self.state.stopwatch_mode:
                bonus = self.state.stopwatch_minutes
                # Incoming player is the one who is NOT currently active
                incoming = 2 if self.state.active_player == 1 else 1
                incoming_key = f"player{incoming}_time"
                incoming_time = getattr(self.state, incoming_key)
                new_time = max(0.0, incoming_time) + bonus
                setattr(self.state, incoming_key, new_time)
                self.logger.log(
                    f"Stopwatch bonus applied: Player {incoming} time set to "
                    f"{new_time:.1f} min (+{bonus:.1f} min overtime bonus)"
                )

            old = self.state.active_player
            self.state.active_player = 2 if old == 1 else 1
            self.state.session_started_at = time.time()
            self.state.break_tokens_p1 = MAX_BREAK_TOKENS
            self.state.break_tokens_p2 = MAX_BREAK_TOKENS
            self.state.stopwatch_mode = False
            self.state.stopwatch_minutes = 0.0
            self.state.stopwatch_started_at = None
            self.state.unfair_break_approved = False

            # Reset alert triggers for the new active player for alerts above their time
            new_active_time_sec = getattr(self.state, f"player{self.state.active_player}_time") * 60.0
            self._triggered_alerts[self.state.active_player] = {
                t for t in self._triggered_alerts[self.state.active_player] if new_active_time_sec <= t
            }

            if self.state.alarm_active:
                self.state.alarm_active = False
                if self.on_alarm_clear:
                    self.on_alarm_clear()

            self.logger.log(
                f"Switched from {self._player_name(old)} to "
                f"{self._player_name(self.state.active_player)}"
            )
            self.save_state()
            self._notify()
            return True, "Player switched."

    def start_break(self, reason: str) -> tuple[bool, str]:
        reason = reason.strip()
        if not reason:
            return False, "Break reason is required."

        with self._lock:
            if self.state.on_break:
                return False, "A break is already in progress."

            player = self.state.active_player
            key = f"break_tokens_p{player}"
            tokens = getattr(self.state, key)
            if tokens <= 0:
                return False, f"No break tokens remaining this session ({MAX_BREAK_TOKENS} max)."

            self.state.on_break = True
            self.state.break_player = player
            self.state.break_reason = reason
            self.state.break_started_at = time.time()
            setattr(self.state, key, tokens - 1)
            self.logger.log(f"Break started (reason: {reason})")
            self.save_state()
            self._notify()
            return True, "Break started."

    def stop_break(self) -> tuple[bool, str]:
        with self._lock:
            if not self.state.on_break:
                return False, "No break in progress."
            self._end_break_internal(forced=False)
            return True, "Break ended."

    def start_unfair_break(self, reason: str, code1: str, code2: str) -> tuple[bool, str]:
        """Start an unfair break if both secret codes are correct."""
        reason = reason.strip()
        if not reason:
            return False, "Break reason is required."

        if not self.verify_both_secrets(code1, code2):
            return False, "Invalid secret codes."

        with self._lock:
            if self.state.on_break:
                return False, "A break is already in progress."

            player = self.state.active_player
            self.state.on_break = True
            self.state.break_player = player
            self.state.break_reason = reason
            self.state.break_started_at = time.time()
            self.state.unfair_break_approved = True
            self.logger.log(f"UNFAIR APPROVED BREAK started (reason: {reason})")
            self.save_state()
            self._notify()
            return True, "Unfair break approved and started."

    def _end_break_internal(self, forced: bool) -> None:
        if not self.state.on_break:
            return
        if forced:
            self.logger.log("Break ended (break allowance exhausted)")
        else:
            self.logger.log("Break ended")
        self.state.on_break = False
        self.state.break_player = None
        self.state.break_reason = ""
        self.state.break_started_at = None
        self.save_state()
        self._notify()

    def enable_stopwatch(self) -> tuple[bool, str]:
        with self._lock:
            if self.state.stopwatch_mode:
                return False, "Stopwatch mode is already enabled."
            self.state.stopwatch_mode = True
            self.logger.log("Stopwatch enabled")
            self.save_state()
            self._notify()
            return True, "Stopwatch enabled."

    def disable_stopwatch(self) -> tuple[bool, str]:
        with self._lock:
            if not self.state.stopwatch_mode:
                return False, "Stopwatch mode is not active."
            self.state.stopwatch_mode = False
            self.logger.log("Stopwatch disabled")
            self.save_state()
            self._notify()
            return True, "Stopwatch disabled."

    def reset_all(self) -> None:
        with self._lock:
            self.state = AppState()
            self._triggered_alerts = {1: set(), 2: set()}
            self.logger.log("Admin reset — all timers restored to defaults")
            if self.on_alarm_clear:
                self.on_alarm_clear()
            self.save_state()
            self._notify()

    def restart_system_state(self) -> None:
        with self._lock:
            self.state = AppState()
            self._triggered_alerts = {1: set(), 2: set()}
            self.logger.log("Admin restart — system state cleared")
            if self.on_alarm_clear:
                self.on_alarm_clear()
            self.save_state()
            self._notify()

    def set_player_times(self, p1: float, p2: float) -> None:
        with self._lock:
            self.state.player1_time = max(0.0, p1)
            self.state.player2_time = max(0.0, p2)
            self.state.player1_depleted = self.state.player1_time <= 0
            self.state.player2_depleted = self.state.player2_time <= 0
            for p, p_time in [(1, p1), (2, p2)]:
                p_sec = p_time * 60.0
                self._triggered_alerts[p] = {t for t in self._triggered_alerts[p] if p_sec <= t}
            self.logger.log(f"Admin edited times: P1={p1:.1f}, P2={p2:.1f}")
            self.save_state()
            self._notify()

    def set_admin_token(self, token: str | None) -> None:
        self.admin_token = token if token else None
        self._save_config()

    def save_network_settings(self, port: int) -> None:
        self.server_port = port
        self._save_config()
