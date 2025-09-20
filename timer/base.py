"""Modulo che definisce la classe base per il countdown dell'app Workout Timer."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass


@dataclass
class WorkoutTimer:
    """Semplice timer a countdown per workout."""

    seconds: int
    label: str | None = None

    def __post_init__(self) -> None:
        if self.seconds < 0:
            raise ValueError("La durata del timer deve essere >= 0 secondi")

    def start(self) -> None:
        """Avvia il countdown, stampando i secondi rimanenti in console."""
        if self.seconds == 0:
            self._emit_message("Timer completato!", final=True)
            return

        for remaining in range(self.seconds, 0, -1):
            self._emit_message(self._format_tick(remaining))
            time.sleep(1)

        self._emit_message("Timer completato!", final=True)

    def _emit_message(self, message: str, *, final: bool = False) -> None:
        prefix = f"[{self.label}] " if self.label else ""
        end = "\n" if final else "\r"
        sys.stdout.write(prefix + message + end)
        sys.stdout.flush()

    @staticmethod
    def _format_tick(remaining: int) -> str:
        minutes, seconds = divmod(remaining, 60)
        return f"{minutes:02d}:{seconds:02d}"
