"""Entry point per l'app Workout Timer con supporto CLI e GUI Tabata."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import customtkinter as ctk

from timer.base import WorkoutTimer


@dataclass
class TabataConfig:
    preparation: int
    work: int
    rest: int
    rounds: int
    cycles: int
    cooldown: int


@dataclass
class Phase:
    label: str
    duration: int


class WorkoutTimerApp(ctk.CTk):
    """GUI che permette di avviare un timer Tabata configurabile."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Workout Timer")
        self.resizable(False, False)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self._after_id: str | None = None
        self._phases: list[Phase] = []
        self._current_phase_index: int = 0
        self._remaining: int = 0

        self._entries: dict[str, ctk.StringVar] = {}

        self._build_widgets()

    def _build_widgets(self) -> None:
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(padx=20, pady=(20, 10), fill="both")

        inputs = [
            ("Preparation (s)", "preparation", "10"),
            ("Work (s)", "work", "20"),
            ("Rest (s)", "rest", "10"),
            ("Rounds", "rounds", "8"),
            ("Cycles", "cycles", "1"),
            ("Cooldown (s)", "cooldown", "0"),
        ]

        for row, (label, key, default) in enumerate(inputs):
            ctk.CTkLabel(form_frame, text=label).grid(row=row, column=0, padx=5, pady=5, sticky="e")
            var = ctk.StringVar(value=default)
            entry = ctk.CTkEntry(form_frame, textvariable=var, width=100)
            entry.grid(row=row, column=1, padx=5, pady=5, sticky="w")
            self._entries[key] = var

        self._time_label = ctk.CTkLabel(self, text="00:00", font=("Helvetica", 40))
        self._time_label.pack(padx=20, pady=(10, 10))

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=(0, 20))

        start_button = ctk.CTkButton(button_frame, text="Start", command=self.start_timer)
        start_button.pack(side="left", padx=10)

        stop_button = ctk.CTkButton(button_frame, text="Stop", command=self.stop_timer)
        stop_button.pack(side="left", padx=10)

    def start_timer(self) -> None:
        config = self._read_config()
        if config is None:
            self._time_label.configure(text="Invalid configuration")
            return

        self._phases = self._build_phases(config)
        if not self._phases:
            self._time_label.configure(text="Nothing to run")
            return

        self._current_phase_index = 0
        self._start_phase()

    def stop_timer(self) -> None:
        self._cancel_timer()
        self._phases = []
        self._current_phase_index = 0
        self._remaining = 0
        self._time_label.configure(text="00:00")

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
        display_time = self._format_time(max(self._remaining, 0))
        self._time_label.configure(text=f"{phase.label} - {display_time}")

    def _read_config(self) -> TabataConfig | None:
        try:
            preparation = self._require_non_negative_int("preparation")
            work = self._require_positive_int("work")
            rest = self._require_non_negative_int("rest")
            rounds = self._require_positive_int("rounds")
            cycles = self._require_positive_int("cycles")
            cooldown = self._require_non_negative_int("cooldown")
        except ValueError:
            return None

        return TabataConfig(
            preparation=preparation,
            work=work,
            rest=rest,
            rounds=rounds,
            cycles=cycles,
            cooldown=cooldown,
        )

    def _build_phases(self, config: TabataConfig) -> list[Phase]:
        phases: list[Phase] = []
        if config.preparation > 0:
            phases.append(Phase("Preparation", config.preparation))

        for cycle in range(1, config.cycles + 1):
            for round_ in range(1, config.rounds + 1):
                cycle_suffix = f" Cycle {cycle}" if config.cycles > 1 else ""
                label = f"Work Round {round_}{cycle_suffix}"
                phases.append(Phase(label, config.work))

                is_last_round = round_ == config.rounds and cycle == config.cycles
                if config.rest > 0 and not is_last_round:
                    rest_label = f"Rest Round {round_}{cycle_suffix}"
                    phases.append(Phase(rest_label, config.rest))

        if config.cooldown > 0:
            phases.append(Phase("Cooldown", config.cooldown))

        return phases

    def _require_positive_int(self, key: str) -> int:
        value = int(self._entries[key].get())
        if value <= 0:
            raise ValueError
        return value

    def _require_non_negative_int(self, key: str) -> int:
        value = int(self._entries[key].get())
        if value < 0:
            raise ValueError
        return value

    def _cancel_timer(self) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    @staticmethod
    def _format_time(seconds: int) -> str:
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Workout Timer con interfaccia grafica Tabata e modalità CLI opzionale",
    )
    parser.add_argument(
        "seconds",
        nargs="?",
        type=int,
        default=30,
        help="Durata in secondi del countdown per la modalità CLI (default: 30)",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Etichetta opzionale per identificare il timer in modalità CLI",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Esegue il timer in modalità console invece della GUI",
    )
    return parser.parse_args()


def launch_gui() -> None:
    app = WorkoutTimerApp()
    app.mainloop()


def main() -> None:
    args = parse_args()
    if args.cli:
        timer = WorkoutTimer(seconds=args.seconds, label=args.label)
        timer.start()
    else:
        launch_gui()


if __name__ == "__main__":
    main()
