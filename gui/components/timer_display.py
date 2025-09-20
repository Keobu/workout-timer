"""Timer display component with phase-aware styling."""

from __future__ import annotations

from typing import Dict

import customtkinter as ctk

_PHASE_COLORS = {
    "idle": ("#1F2933", "#CBD2D9"),
    "prep": ("#F59E0B", "#102A43"),
    "work": ("#10B981", "#062C22"),
    "rest": ("#3B82F6", "#0B1F3A"),
    "cooldown": ("#EF4444", "#2C0F0F"),
    "finish": ("#8B5CF6", "#1F1636"),
}


class TimerDisplay(ctk.CTkFrame):
    """Large timer label with phase feedback and simple animations."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color="#101725", border_width=1, border_color="#243B53")
        self._phase_color = "idle"
        self._animation_after: str | None = None

        self._time_label = ctk.CTkLabel(self, text="00:00", font=("SF Pro Display", 88, "bold"))
        self._time_label.pack(padx=24, pady=(36, 12))

        self._phase_label = ctk.CTkLabel(
            self,
            text="Ready",
            font=("SF Pro Text", 22),
            text_color="#9AA5B1",
        )
        self._phase_label.pack(padx=16, pady=(0, 24))

    # Public API ---------------------------------------------------------

    def set_time(self, time_str: str) -> None:
        self._time_label.configure(text=time_str)

    def set_phase(self, phase_kind: str, label: str) -> None:
        self._phase_label.configure(text=label)
        self._phase_color = phase_kind
        self._apply_colors()
        self.flash()

    def reset(self) -> None:
        self._cancel_animation()
        self._phase_label.configure(text="Ready")
        self._phase_color = "idle"
        self._time_label.configure(text="00:00")
        self._apply_colors()

    def set_font_scale(self, scale: float) -> None:
        base_time = int(88 * scale)
        base_phase = int(22 * scale)
        self._time_label.configure(font=("SF Pro Display", max(base_time, 40), "bold"))
        self._phase_label.configure(font=("SF Pro Text", max(base_phase, 14)))

    def flash(self) -> None:
        self._cancel_animation()
        self.configure(fg_color=_PHASE_COLORS.get(self._phase_color, _PHASE_COLORS["idle"])[0])
        self._time_label.configure(text_color="#0B0B0B")
        self._phase_label.configure(text_color="#0B0B0B")
        self._animation_after = self.after(220, self._apply_colors)

    # Internal helpers ---------------------------------------------------

    def _apply_colors(self) -> None:
        self._animation_after = None
        fg, text = _PHASE_COLORS.get(self._phase_color, _PHASE_COLORS["idle"])
        self.configure(fg_color=fg)
        self._time_label.configure(text_color="#FFFFFF")
        self._phase_label.configure(text_color=text)

    def _cancel_animation(self) -> None:
        if self._animation_after is not None:
            try:
                self.after_cancel(self._animation_after)
            except Exception:  # pragma: no cover - defensive
                pass
            self._animation_after = None
