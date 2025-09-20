"""Mode configuration forms for Workout Timer."""

from __future__ import annotations

from typing import Callable, List

import customtkinter as ctk

from timer.base import BoxingConfig, TabataConfig
from timer.base import BoxingTimer, CustomTimer, Phase, TabataTimer

from gui.utils import parse_duration


class BaseModeForm(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color="transparent")
        self._callbacks: list[Callable[[], None]] = []

    def bind_on_change(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def _notify_change(self) -> None:
        for callback in self._callbacks:
            callback()

    def set_font_scale(self, scale: float) -> None:
        # Subclasses override if they maintain custom fonts.
        pass


class TabataForm(BaseModeForm):
    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master)
        self._entries: dict[str, ctk.StringVar] = {}
        self._build()

    def _build(self) -> None:
        fields = [
            ("Preparation", "preparation", "10"),
            ("Work", "work", "20"),
            ("Rest", "rest", "10"),
            ("Rounds", "rounds", "8"),
            ("Cycles", "cycles", "1"),
            ("Cooldown", "cooldown", "0"),
        ]
        for row, (label, key, default) in enumerate(fields):
            ctk.CTkLabel(self, text=f"{label}").grid(row=row, column=0, sticky="e", padx=6, pady=4)
            var = ctk.StringVar(master=self, value=default)
            entry = ctk.CTkEntry(self, textvariable=var, width=120)
            entry.grid(row=row, column=1, sticky="w", padx=6, pady=4)
            var.trace_add("write", lambda *_args: self._notify_change())
            self._entries[key] = var

    def get_config(self) -> TabataConfig:
        try:
            prep = parse_duration(self._entries["preparation"].get())
            work = parse_duration(self._entries["work"].get())
            rest = parse_duration(self._entries["rest"].get())
            rounds = int(self._entries["rounds"].get())
            cycles = int(self._entries["cycles"].get())
            cooldown = parse_duration(self._entries["cooldown"].get())
        except ValueError as exc:
            raise ValueError(f"Tabata form: {exc}")
        return TabataConfig(
            preparation=prep,
            work=work,
            rest=rest,
            rounds=rounds,
            cycles=cycles,
            cooldown=cooldown,
        )

    def estimate_phases(self) -> List[Phase]:
        config = self.get_config()
        return TabataTimer(config).phases


class BoxingForm(BaseModeForm):
    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master)
        self._entries: dict[str, ctk.StringVar] = {}
        self._build()

    def _build(self) -> None:
        fields = [
            ("Work", "work", "3:00"),
            ("Rest", "rest", "1:00"),
            ("Rounds", "rounds", "3"),
        ]
        for row, (label, key, default) in enumerate(fields):
            ctk.CTkLabel(self, text=f"{label}").grid(row=row, column=0, sticky="e", padx=6, pady=4)
            var = ctk.StringVar(master=self, value=default)
            entry = ctk.CTkEntry(self, textvariable=var, width=120)
            entry.grid(row=row, column=1, sticky="w", padx=6, pady=4)
            var.trace_add("write", lambda *_args: self._notify_change())
            self._entries[key] = var

    def get_config(self) -> BoxingConfig:
        try:
            work = parse_duration(self._entries["work"].get())
            rest = parse_duration(self._entries["rest"].get())
            rounds = int(self._entries["rounds"].get())
        except ValueError as exc:
            raise ValueError(f"Boxing form: {exc}")
        return BoxingConfig(work=work, rest=rest, rounds=rounds)

    def estimate_phases(self) -> List[Phase]:
        config = self.get_config()
        return BoxingTimer(config).phases


class CustomForm(BaseModeForm):
    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master)
        self._textbox = ctk.CTkTextbox(self, width=260, height=200)
        self._textbox.insert("1.0", "1:00, 0:30\n45, 15\n60, 0")
        self._textbox.pack(fill="both", expand=True, padx=4, pady=4)
        self._textbox.bind("<<Modified>>", self._on_modified)

    def _on_modified(self, event: object) -> None:
        widget = getattr(event, "widget", None)
        if widget is not None:
            try:
                widget.edit_modified(False)
            except Exception:
                pass
        self._notify_change()

    def get_intervals(self) -> list[tuple[int, int]]:
        content = self._textbox.get("1.0", "end").strip()
        if not content:
            raise ValueError("Custom form: provide at least one interval")
        intervals: list[tuple[int, int]] = []
        for idx, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if "," in stripped:
                work_str, rest_str = [part.strip() for part in stripped.split(",", 1)]
            else:
                parts = stripped.split()
                if len(parts) not in (1, 2):
                    raise ValueError(f"Line {idx}: expected 'work rest'")
                work_str = parts[0]
                rest_str = parts[1] if len(parts) == 2 else "0"
            try:
                work = parse_duration(work_str)
                rest = parse_duration(rest_str) if rest_str else 0
            except ValueError as exc:
                raise ValueError(f"Line {idx}: {exc}")
            if work <= 0:
                raise ValueError(f"Line {idx}: work must be > 0")
            if rest < 0:
                raise ValueError(f"Line {idx}: rest must be >= 0")
            intervals.append((work, rest))
        if not intervals:
            raise ValueError("Custom form: no valid intervals found")
        return intervals

    def estimate_phases(self) -> List[Phase]:
        intervals = self.get_intervals()
        return CustomTimer(intervals).phases


class TopicsForm(BaseModeForm):
    """Topics/educational page for workout information."""
    
    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master)
        self._build()
    
    def _build(self) -> None:
        # Title
        title = ctk.CTkLabel(
            self, 
            text="Workout Topics & Information", 
            font=("SF Pro Text", 24, "bold")
        )
        title.pack(pady=(20, 30))
        
        # Create a scrollable frame for content
        self._scrollable_frame = ctk.CTkScrollableFrame(self)
        self._scrollable_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Add topic sections
        self._add_topic_section("Tabata Training", [
            "• High-intensity interval training protocol",
            "• 20 seconds of intense exercise, 10 seconds rest",
            "• Usually performed for 8 rounds (4 minutes total)",
            "• Improves both aerobic and anaerobic fitness",
            "• Originally developed by Dr. Izumi Tabata"
        ])
        
        self._add_topic_section("Boxing Training", [
            "• Traditional boxing round structure",
            "• Typically 3-minute rounds with 1-minute rest",
            "• Excellent for cardiovascular fitness",
            "• Improves coordination and reflexes",
            "• Can be adapted for different fitness levels"
        ])
        
        self._add_topic_section("Custom Workouts", [
            "• Create your own interval patterns",
            "• Mix different work and rest periods",
            "• Ideal for sport-specific training",
            "• Can target specific energy systems",
            "• Allows for progressive overload"
        ])
        
        self._add_topic_section("General Tips", [
            "• Always warm up before intense exercise",
            "• Stay hydrated throughout your workout",
            "• Listen to your body and rest when needed",
            "• Gradually increase intensity over time",
            "• Cool down properly after exercise"
        ])
    
    def _add_topic_section(self, title: str, points: list[str]) -> None:
        # Section title
        section_title = ctk.CTkLabel(
            self._scrollable_frame,
            text=title,
            font=("SF Pro Text", 18, "bold"),
            anchor="w"
        )
        section_title.pack(fill="x", pady=(20, 10), padx=10)
        
        # Section content
        for point in points:
            point_label = ctk.CTkLabel(
                self._scrollable_frame,
                text=point,
                font=("SF Pro Text", 14),
                anchor="w"
            )
            point_label.pack(fill="x", pady=2, padx=20)
    
    def estimate_phases(self) -> List[Phase]:
        # Topics page doesn't have phases to estimate
        return []
