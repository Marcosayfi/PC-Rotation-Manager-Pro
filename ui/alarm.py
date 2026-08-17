"""Looping chime sound when an alert or time-up alarm triggers."""

from __future__ import annotations

import struct
import threading
import wave
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
TIME_UP_PATH = ASSETS_DIR / "alarm.wav"
CHIME_PATH = ASSETS_DIR / "chime.wav"

BUILTIN_ALARM_SOUNDS = (
    {"id": "time_up", "name": "Time's up", "path": str(TIME_UP_PATH)},
    {"id": "chime", "name": "Chime", "path": str(CHIME_PATH)},
)
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg"}


def ensure_chime_wav() -> Path:
    """Create a high quality dual-tone chime sound if missing."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    if CHIME_PATH.exists():
        return CHIME_PATH

    sample_rate = 22050
    duration = 0.8
    frames = int(sample_rate * duration)
    samples: list[int] = []
    import math

    # Two-tone melodic chime: E5 (659.25Hz) followed by A5 (880Hz)
    for i in range(frames):
        t = i / sample_rate
        if t < 0.35:
            freq = 659.25
            decay = math.exp(-t * 5.0)
        else:
            freq = 880.0
            decay = math.exp(-(t - 0.35) * 4.5)

        val = int(32767 * 0.85 * decay * math.sin(2 * math.pi * freq * t))
        samples.append(val)

    with wave.open(str(CHIME_PATH), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(struct.pack("<h", s) for s in samples))

    return CHIME_PATH


def default_alarm_sound_path() -> Path:
    """Return the default alarm sound, falling back to the generated chime."""
    ensure_chime_wav()
    if TIME_UP_PATH.exists():
        return TIME_UP_PATH
    return CHIME_PATH


def resolve_alarm_sound_path(sound_id: str, custom_sounds: list[dict[str, str]] | None = None) -> Path:
    """Resolve a built-in or custom sound id to a playable audio path."""
    ensure_chime_wav()
    if sound_id == "chime":
        return CHIME_PATH
    if sound_id == "time_up":
        return default_alarm_sound_path()

    for sound in custom_sounds or []:
        if sound_id in {sound.get("id"), sound.get("path")}:
            path = Path(sound.get("path", ""))
            if path.exists():
                return path
            break

    return default_alarm_sound_path()


class AlarmPlayer:
    def __init__(self, sound_path: str | Path | None = None) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._playing = False
        self._sound_path = Path(sound_path) if sound_path else default_alarm_sound_path()
        self._media_player = None
        self._audio_output = None
        self._media_restart_handler = None
        self._media_error_handler = None
        ensure_chime_wav()

    @property
    def is_playing(self) -> bool:
        return self._playing

    def set_sound_path(self, sound_path: str | Path) -> None:
        self._sound_path = Path(sound_path)

    def start(self, sound_path: str | Path | None = None) -> None:
        if sound_path:
            self.set_sound_path(sound_path)
        if self._playing:
            return
        self._stop.clear()
        self._playing = True
        if self._sound_path.suffix.lower() != ".wav" and self._start_media_loop():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="alarm")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._playing = False
        self._stop_media_loop()
        try:
            import winsound

            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

    def _start_media_loop(self) -> bool:
        sound_path = self._sound_path
        if not sound_path.exists():
            return False

        try:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
        except Exception:
            return False

        try:
            self._media_player = QMediaPlayer()
            self._audio_output = QAudioOutput()
            self._audio_output.setVolume(1.0)
            self._media_player.setAudioOutput(self._audio_output)
            self._media_player.setSource(QUrl.fromLocalFile(str(sound_path)))

            def fallback_to_tones(*_args) -> None:
                if not self._playing or self._thread is not None:
                    return
                self._stop_media_loop()
                self._thread = threading.Thread(target=self._loop, daemon=True, name="alarm")
                self._thread.start()

            self._media_error_handler = fallback_to_tones
            self._media_player.errorOccurred.connect(fallback_to_tones)

            try:
                infinite_loops = getattr(getattr(QMediaPlayer, "Loops", None), "Infinite", -1)
                self._media_player.setLoops(infinite_loops)
            except Exception:
                def restart(status) -> None:
                    if status == QMediaPlayer.MediaStatus.EndOfMedia and self._playing:
                        self._media_player.setPosition(0)
                        self._media_player.play()

                self._media_restart_handler = restart
                self._media_player.mediaStatusChanged.connect(restart)

            self._media_player.play()
            return True
        except Exception:
            self._stop_media_loop()
            return False

    def _stop_media_loop(self) -> None:
        if self._media_player is None:
            return
        try:
            self._media_player.stop()
            self._media_player.deleteLater()
        except Exception:
            pass
        try:
            if self._audio_output is not None:
                self._audio_output.deleteLater()
        except Exception:
            pass
        self._media_player = None
        self._audio_output = None
        self._media_restart_handler = None
        self._media_error_handler = None

    def _loop(self) -> None:
        """Continuously loop WAV or fallback tones until dismissed."""
        try:
            import winsound

            sound_path = self._sound_path
            if sound_path.exists():
                loop_path = sound_path
            elif CHIME_PATH.exists():
                loop_path = CHIME_PATH
            else:
                loop_path = None

            if loop_path is not None:
                flags = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP
                winsound.PlaySound(str(loop_path), flags)
                while not self._stop.is_set():
                    self._stop.wait(0.1)
            else:
                while not self._stop.is_set():
                    winsound.Beep(659, 200)
                    winsound.Beep(880, 300)
        except Exception:
            while not self._stop.is_set():
                try:
                    import winsound

                    winsound.Beep(659, 200)
                    winsound.Beep(880, 300)
                except Exception:
                    print("\a", end="", flush=True)
        finally:
            try:
                import winsound

                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
            self._playing = False
