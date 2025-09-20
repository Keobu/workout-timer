"""Entry point per l'app Workout Timer con supporto CLI e GUI."""

from __future__ import annotations

import argparse

import customtkinter as ctk

from timer.base import WorkoutTimer


class WorkoutTimerApp(ctk.CTk):
    """Semplice GUI con countdown di prova."""

    def __init__(self, *, countdown_seconds: int = 10) -> None:
        super().__init__()
        self.title("Workout Timer")
        self.resizable(False, False)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self._initial_seconds = countdown_seconds
        self._remaining = 0
        self._after_id: str | None = None

        self._build_widgets()

    def _build_widgets(self) -> None:
        self._time_label = ctk.CTkLabel(self, text="00:00", font=("Helvetica", 48))
        self._time_label.pack(padx=20, pady=(20, 10))

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=(0, 20))

        start_button = ctk.CTkButton(button_frame, text="Start", command=self.start_timer)
        start_button.pack(side="left", padx=10)

        stop_button = ctk.CTkButton(button_frame, text="Stop", command=self.stop_timer)
        stop_button.pack(side="left", padx=10)

    def start_timer(self) -> None:
        self._cancel_timer()
        self._remaining = self._initial_seconds
        self._tick()

    def stop_timer(self) -> None:
        self._cancel_timer()
        self._remaining = 0
        self._time_label.configure(text="00:00")

    def _tick(self) -> None:
        self._time_label.configure(text=self._format_time(self._remaining))
        if self._remaining > 0:
            self._remaining -= 1
            self._after_id = self.after(1000, self._tick)
        else:
            self._after_id = None

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
        description="Workout Timer con interfaccia grafica e modalità CLI opzionale",
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
