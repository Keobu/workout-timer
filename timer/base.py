"""Timer utilities and workout-specific countdown builders."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class Phase:
    """Represents a labeled segment of time in seconds."""

    label: str
    duration: int
    kind: str = "work"

    def __post_init__(self) -> None:
        if self.duration < 0:
            raise ValueError("Phase duration must be >= 0 seconds")
        if not self.kind:
            raise ValueError("Phase kind must be a non-empty string")


class WorkoutTimer:
    """Base countdown timer that iterates through labeled phases."""

    def __init__(self, phases: Iterable[Phase], *, label: str | None = None) -> None:
        self._phases: List[Phase] = [phase for phase in phases if phase.duration > 0]
        self._label = label

    @property
    def phases(self) -> List[Phase]:
        return list(self._phases)

    def start(self) -> None:
        if not self._phases:
            self._emit_message("Timer completed!", final=True)
            return

        for phase in self._phases:
            for remaining in range(phase.duration, 0, -1):
                self._emit_message(self._format_output(phase.label, remaining))
                time.sleep(1)

        self._emit_message("Timer completed!", final=True)

    def _emit_message(self, message: str, *, final: bool = False) -> None:
        prefix = f"[{self._label}] " if self._label else ""
        end = "\n" if final else "\r"
        sys.stdout.write(prefix + message + end)
        sys.stdout.flush()

    @staticmethod
    def _format_output(label: str, remaining: int) -> str:
        minutes, seconds = divmod(remaining, 60)
        return f"{label}: {minutes:02d}:{seconds:02d}"


class CountdownTimer(WorkoutTimer):
    """Simple countdown over a single phase."""

    def __init__(self, seconds: int, *, label: str | None = None) -> None:
        if seconds < 0:
            raise ValueError("Timer duration must be >= 0 seconds")
        phase_label = label or "Countdown"
        phases = [Phase(phase_label, seconds)] if seconds > 0 else []
        super().__init__(phases, label=label)


@dataclass(frozen=True)
class TabataConfig:
    preparation: int
    work: int
    rest: int
    rounds: int
    cycles: int
    cooldown: int

    def __post_init__(self) -> None:
        if self.preparation < 0 or self.rest < 0 or self.cooldown < 0:
            raise ValueError("Preparation, rest, and cooldown must be >= 0")
        if self.work <= 0:
            raise ValueError("Work duration must be > 0")
        if self.rounds <= 0 or self.cycles <= 0:
            raise ValueError("Rounds and cycles must be > 0")


class TabataTimer(WorkoutTimer):
    """Tabata protocol builder."""

    def __init__(self, config: TabataConfig) -> None:
        phases = self._build_phases(config)
        super().__init__(phases)

    @staticmethod
    def _build_phases(config: TabataConfig) -> List[Phase]:
        phases: List[Phase] = []
        if config.preparation > 0:
            phases.append(Phase("Preparation", config.preparation, "prep"))

        for cycle in range(1, config.cycles + 1):
            cycle_suffix = f" Cycle {cycle}" if config.cycles > 1 else ""
            for round_idx in range(1, config.rounds + 1):
                phases.append(
                    Phase(
                        f"Work Round {round_idx}{cycle_suffix}",
                        config.work,
                        "work",
                    )
                )
                is_last = cycle == config.cycles and round_idx == config.rounds
                if config.rest > 0 and not is_last:
                    phases.append(
                        Phase(
                            f"Rest Round {round_idx}{cycle_suffix}",
                            config.rest,
                            "rest",
                        )
                    )

        if config.cooldown > 0:
            phases.append(Phase("Cooldown", config.cooldown, "cooldown"))

        return phases


@dataclass(frozen=True)
class BoxingConfig:
    work: int
    rest: int
    rounds: int

    def __post_init__(self) -> None:
        if self.work <= 0:
            raise ValueError("Work duration must be > 0")
        if self.rest < 0:
            raise ValueError("Rest duration must be >= 0")
        if self.rounds <= 0:
            raise ValueError("Rounds must be > 0")


class BoxingTimer(WorkoutTimer):
    """Classic boxing round timer."""

    def __init__(self, config: BoxingConfig) -> None:
        phases = self._build_phases(config)
        super().__init__(phases)

    @staticmethod
    def _build_phases(config: BoxingConfig) -> List[Phase]:
        phases: List[Phase] = []
        for round_idx in range(1, config.rounds + 1):
            phases.append(Phase(f"Work Round {round_idx}", config.work, "work"))
            if config.rest > 0 and round_idx < config.rounds:
                phases.append(Phase(f"Rest Round {round_idx}", config.rest, "rest"))
        return phases


class CustomTimer(WorkoutTimer):
    """Timer for user-provided (work, rest) pairs."""

    def __init__(self, intervals: Sequence[tuple[int, int]]) -> None:
        phases = self._build_phases(intervals)
        super().__init__(phases)

    @staticmethod
    def _build_phases(intervals: Sequence[tuple[int, int]]) -> List[Phase]:
        if not intervals:
            raise ValueError("At least one interval is required")

        phases: List[Phase] = []
        for idx, (work, rest) in enumerate(intervals, start=1):
            if work <= 0:
                raise ValueError("Work duration in custom intervals must be > 0")
            if rest < 0:
                raise ValueError("Rest duration in custom intervals must be >= 0")

            phases.append(Phase(f"Work Interval {idx}", work, "work"))
            if rest > 0 and idx < len(intervals):
                phases.append(Phase(f"Rest Interval {idx}", rest, "rest"))

        return phases
