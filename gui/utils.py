"""Utility helpers for Workout Timer GUI."""

from __future__ import annotations

from typing import Iterable

from timer.base import Phase


def parse_duration(value: str) -> int:
    """Parse seconds from input supporting mm:ss, hh:mm:ss, and suffixes."""

    cleaned = value.strip().lower()
    if not cleaned:
        raise ValueError("Value must not be empty")

    if ":" in cleaned:
        if cleaned.endswith("s") or cleaned.endswith("m"):
            raise ValueError("Use mm:ss or plain seconds for durations")
        parts = cleaned.split(":")
        if not all(part.isdigit() for part in parts):
            raise ValueError("Use digits in mm:ss format")
        total = 0
        for part in parts:
            total = total * 60 + int(part)
        return total

    multiplier = 1
    if cleaned.endswith("m"):
        multiplier = 60
        cleaned = cleaned[:-1]
    elif cleaned.endswith("s"):
        cleaned = cleaned[:-1]

    if not cleaned.isdigit():
        raise ValueError("Duration must be numeric")
    return int(cleaned) * multiplier


def format_seconds(seconds: int, *, include_hours: bool = True) -> str:
    if seconds < 0:
        seconds = 0
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if include_hours and hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def summarize_phases(phases: Iterable[Phase]) -> dict[str, int]:
    totals: dict[str, int] = {"prep": 0, "work": 0, "rest": 0, "cooldown": 0, "other": 0}
    for phase in phases:
        key = phase.kind if phase.kind in totals else "other"
        totals[key] += phase.duration
    return totals
