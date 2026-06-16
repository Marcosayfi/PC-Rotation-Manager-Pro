"""Looping alarm sound when a player's time reaches zero."""

from __future__ import annotations

import struct
import threading
import wave
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ALARM_PATH = ASSETS_DIR / "alarm.wav"


def ensure_alarm_wav() -> Path:
    """Create a loud multi-tone alarm WAV if missing."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    if ALARM_PATH.exists():
        return ALARM_PATH

    sample_rate = 22050
    duration = 0.35
    frames = int(sample_rate * duration)
    samples: list[int] = []
    for i in range(frames):
        t = i / sample_rate
        # Alternating high tones for urgency
        freq = 880.0 if int(t * 8) % 2 == 0 else 1100.0
        val = int(32767 * 0.85 * (1 if (int(t * 16) % 2 == 0) else 0.6))
        import math

        sample = int(val * math.sin(2 * math.pi * freq * t))
        samples.append(sample)

    with wave.open(str(ALARM_PATH), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(struct.pack("<h", s) for s in samples))

    return ALARM_PATH


class AlarmPlayer:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._playing = False
        ensure_alarm_wav()

    @property
    def is_playing(self) -> bool:
        return self._playing

    def start(self) -> None:
        if self._playing:
            return
        self._stop.clear()
        self._playing = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="alarm")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._playing = False
        try:
            import winsound

            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

    def _loop(self) -> None:
        try:
            import winsound

            if ALARM_PATH.exists():
                flags = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP
                winsound.PlaySound(str(ALARM_PATH), flags)
                while not self._stop.is_set():
                    self._stop.wait(0.2)
            else:
                while not self._stop.is_set():
                    winsound.Beep(1100, 400)
                    winsound.Beep(880, 400)
        except Exception:
            while not self._stop.is_set():
                try:
                    import winsound

                    winsound.Beep(1100, 500)
                    winsound.Beep(880, 500)
                except Exception:
                    print("\a", end="", flush=True)
                self._stop.wait(0.3)
        finally:
            self._playing = False
