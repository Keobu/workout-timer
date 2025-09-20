"""Entry point for the Workout Timer app with CLI and multi-mode GUI."""

from __future__ import annotations

import argparse
from typing import Iterable, List

import customtkinter as ctk

from timer.base import (
    BoxingConfig,
    BoxingTimer,
    CountdownTimer,
    CustomTimer,
    Phase,
    TabataConfig,
    TabataTimer,
)


class WorkoutTimerApp(ctk.CTk):
    """GUI supporting Tabata, Boxing, and Custom timer configurations."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Workout Timer")
        self.resizable(False, False)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self._after_id: str | None = None
        self._phases: List[Phase] = []
        self._current_phase_index: int = 0
        self._remaining: int = 0

        self._entries: dict[str, dict[str, ctk.StringVar]] = {
            "Tabata": {},
            "Boxing": {},
        }
        self._custom_text: ctk.CTkTextbox | None = None

        self._build_widgets()

    def _build_widgets(self) -> None:
        self._mode_tabs = ctk.CTkTabview(self)
        self._mode_tabs.pack(padx=20, pady=(20, 10), fill="both", expand=False)

        tab_tabata = self._mode_tabs.add("Tabata")
        self._build_tabata_inputs(tab_tabata)

        tab_boxing = self._mode_tabs.add("Boxing")
        self._build_boxing_inputs(tab_boxing)

        tab_custom = self._mode_tabs.add("Custom")
        self._build_custom_inputs(tab_custom)

        self._time_label = ctk.CTkLabel(self, text="00:00", font=("Helvetica", 40))
        self._time_label.pack(padx=20, pady=(10, 10))

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=(0, 20))

        start_button = ctk.CTkButton(button_frame, text="Start", command=self.start_timer)
        start_button.pack(side="left", padx=10)

        stop_button = ctk.CTkButton(button_frame, text="Stop", command=self.stop_timer)
        stop_button.pack(side="left", padx=10)

    def _build_tabata_inputs(self, parent: ctk.CTkFrame) -> None:
        inputs = [
            ("Preparation (s)", "preparation", "10"),
            ("Work (s)", "work", "20"),
            ("Rest (s)", "rest", "10"),
            ("Rounds", "rounds", "8"),
            ("Cycles", "cycles", "1"),
            ("Cooldown (s)", "cooldown", "0"),
        ]

        for row, (label, key, default) in enumerate(inputs):
            ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=5, pady=5, sticky="e")
            var = ctk.StringVar(value=default)
            entry = ctk.CTkEntry(parent, textvariable=var, width=110)
            entry.grid(row=row, column=1, padx=5, pady=5, sticky="w")
            self._entries["Tabata"][key] = var

    def _build_boxing_inputs(self, parent: ctk.CTkFrame) -> None:
        inputs = [
            ("Work (s)", "work", "180"),
            ("Rest (s)", "rest", "60"),
            ("Rounds", "rounds", "3"),
        ]

        for row, (label, key, default) in enumerate(inputs):
            ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=5, pady=5, sticky="e")
            var = ctk.StringVar(value=default)
            entry = ctk.CTkEntry(parent, textvariable=var, width=110)
            entry.grid(row=row, column=1, padx=5, pady=5, sticky="w")
            self._entries["Boxing"][key] = var

    def _build_custom_inputs(self, parent: ctk.CTkFrame) -> None:
        info = (
            "One interval per line. Use 'work, rest' seconds (rest optional).\n"
            "Example: 45, 15"
        )
        ctk.CTkLabel(parent, text=info, justify="left").grid(
            row=0, column=0, padx=5, pady=(5, 10), sticky="w"
        )
        self._custom_text = ctk.CTkTextbox(parent, width=260, height=160)
        self._custom_text.grid(row=1, column=0, padx=5, pady=5)
        self._custom_text.insert("1.0", "45, 15\n30, 10\n60, 0")

    def start_timer(self) -> None:
        try:
            phases = self._phases_for_selected_mode()
        except ValueError as error:
            self._display_error(str(error))
            return

        if not phases:
            self._display_error("Nothing to run")
            return

        self._phases = list(phases)
        self._current_phase_index = 0
        self._start_phase()

    def stop_timer(self) -> None:
        self._cancel_timer()
        self._phases = []
        self._current_phase_index = 0
        self._remaining = 0
        self._time_label.configure(text="00:00")

    def _phases_for_selected_mode(self) -> Iterable[Phase]:
        mode = self._mode_tabs.get()
        if mode == "Tabata":
            config = self._read_tabata_config()
            timer = TabataTimer(config)
        elif mode == "Boxing":
            config = self._read_boxing_config()
            timer = BoxingTimer(config)
        else:
            intervals = self._read_custom_intervals()
            timer = CustomTimer(intervals)
        return timer.phases

    def _start_phase(self) -> None:
        self._cancel_timer()
        if self._current_phase_index >= len(self._phases):
            self._time_label.configure(text="Done")
            return

        phase = self._phases[self._current_phase_index]
        self._remaining = phase.duration
        self._update_display()
        self._schedule_tick()

    def _schedule_tick(self) -> None:
        self._after_id = self.after(1000, self._tick)

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining >= 0:
            self._update_display()

        if self._remaining <= 0:
            self._current_phase_index += 1
            if self._current_phase_index < len(self._phases):
                self._start_phase()
            else:
                self._cancel_timer()
                self._time_label.configure(text="Done")
        else:
            self._schedule_tick()

    def _update_display(self) -> None:
        phase = self._phases[self._current_phase_index]
        minutes, seconds = divmod(max(self._remaining, 0), 60)
        self._time_label.configure(
            text=f"{phase.label} - {minutes:02d}:{seconds:02d}"
        )

    def _display_error(self, message: str) -> None:
        self._cancel_timer()
        self._time_label.configure(text=message)

    def _read_tabata_config(self) -> TabataConfig:
        entries = self._entries["Tabata"]
        return TabataConfig(
            preparation=self._get_int(entries["preparation"], name="Preparation", allow_zero=True),
            work=self._get_int(entries["work"], name="Work", positive=True),
            rest=self._get_int(entries["rest"], name="Rest", allow_zero=True),
            rounds=self._get_int(entries["rounds"], name="Rounds", positive=True),
            cycles=self._get_int(entries["cycles"], name="Cycles", positive=True),
            cooldown=self._get_int(entries["cooldown"], name="Cooldown", allow_zero=True),
        )

    def _read_boxing_config(self) -> BoxingConfig:
        entries = self._entries["Boxing"]
        return BoxingConfig(
            work=self._get_int(entries["work"], name="Work", positive=True),
            rest=self._get_int(entries["rest"], name="Rest", allow_zero=True),
            rounds=self._get_int(entries["rounds"], name="Rounds", positive=True),
        )

    def _read_custom_intervals(self) -> List[tuple[int, int]]:
        if self._custom_text is None:
            raise ValueError("Custom input not available")

        content = self._custom_text.get("1.0", "end").strip()
        if not content:
            raise ValueError("Provide at least one interval")

        intervals: List[tuple[int, int]] = []
        for idx, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.replace(",", " ").split()
            if len(parts) not in (1, 2):
                raise ValueError(f"Line {idx}: expected 'work rest' values")
            try:
                work = int(parts[0])
                rest = int(parts[1]) if len(parts) == 2 else 0
            except ValueError as exc:
                raise ValueError(f"Line {idx}: invalid integer value") from exc
            if work <= 0:
                raise ValueError(f"Line {idx}: work must be > 0")
            if rest < 0:
                raise ValueError(f"Line {idx}: rest must be >= 0")
            intervals.append((work, rest))

        if not intervals:
            raise ValueError("Provide at least one interval")

        return intervals

    @staticmethod
    def _get_int(
        var: ctk.StringVar,
        *,
        name: str,
        positive: bool = False,
        allow_zero: bool = False,
    ) -> int:
        value_str = var.get().strip()
        try:
            value = int(value_str)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer") from exc
        if positive:
            if value <= 0:
                raise ValueError(f"{name} must be > 0")
            return value
        if allow_zero:
            if value < 0:
                raise ValueError(f"{name} must be >= 0")
            return value
        if value <= 0:
            raise ValueError(f"{name} must be > 0")
        return value

    def _cancel_timer(self) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Workout Timer with GUI (Tabata, Boxing, Custom) and optional CLI mode",
    )
    parser.add_argument(
        "seconds",
        nargs="?",
        type=int,
        default=30,
        help="Countdown duration in seconds for CLI mode (default: 30)",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Optional label for the CLI countdown",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run the timer in console mode instead of launching the GUI",
    )
    return parser.parse_args()


def launch_gui() -> None:
    app = WorkoutTimerApp()
    app.mainloop()


def main() -> None:
    args = parse_args()
    if args.cli:
        timer = CountdownTimer(seconds=args.seconds, label=args.label)
        timer.start()
    else:
        launch_gui()


if __name__ == "__main__":
    main()
