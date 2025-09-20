"""Entry point for the Workout Timer app with CLI, multi-mode GUI, and settings."""

from __future__ import annotations

import argparse
from pathlib import Path
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

from gui.settings import (
    SettingsPanel,
    SettingsStore,
    SoundPlayer,
    SoundSettings,
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SOUND_PATH = BASE_DIR / "assets" / "beep.wav"
SETTINGS_PATH = BASE_DIR / "settings.json"


class WorkoutTimerApp(ctk.CTk):
    """GUI supporting Tabata, Boxing, Custom timers, and configurable settings."""

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
        self._total_labels: dict[str, dict[str, ctk.CTkLabel]] = {
            "Tabata": {},
            "Boxing": {},
            "Custom": {},
        }
        self._custom_text: ctk.CTkTextbox | None = None
        self._tab_command = None

        self._settings_store = SettingsStore(SETTINGS_PATH, DEFAULT_SOUND_PATH)
        self._settings: SoundSettings = self._settings_store.load()
        self._sound_player = SoundPlayer(
            self._settings, DEFAULT_SOUND_PATH, on_fail=self.bell
        )
        self._settings_panel: SettingsPanel | None = None

        self._build_widgets()
        self._update_mode_totals()

    def _build_widgets(self) -> None:
        self._main_tabs = ctk.CTkTabview(self)
        self._main_tabs.pack(padx=20, pady=(20, 10), fill="both", expand=False)

        timer_tab = self._main_tabs.add("Timer")
        settings_tab = self._main_tabs.add("Settings")

        self._build_timer_tab(timer_tab)
        self._build_settings_tab(settings_tab)

    def _build_timer_tab(self, parent: ctk.CTkFrame) -> None:
        self._mode_tabs = ctk.CTkTabview(parent)
        self._mode_tabs.pack(padx=10, pady=(10, 10), fill="both", expand=False)

        segmented_button = getattr(self._mode_tabs, "_segmented_button", None)
        default_command = getattr(self._mode_tabs, "_set_tab", None)
        if segmented_button is not None and default_command is not None:
            self._tab_command = default_command
            segmented_button.configure(command=self._on_mode_change)

        tab_tabata = self._mode_tabs.add("Tabata")
        self._build_tabata_inputs(tab_tabata)

        tab_boxing = self._mode_tabs.add("Boxing")
        self._build_boxing_inputs(tab_boxing)

        tab_custom = self._mode_tabs.add("Custom")
        self._build_custom_inputs(tab_custom)

        self._time_label = ctk.CTkLabel(parent, text="00:00", font=("Helvetica", 40))
        self._time_label.pack(padx=10, pady=(10, 10))

        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.pack(pady=(0, 15))

        start_button = ctk.CTkButton(button_frame, text="Start", command=self.start_timer)
        start_button.pack(side="left", padx=10)

        stop_button = ctk.CTkButton(button_frame, text="Stop", command=self.stop_timer)
        stop_button.pack(side="left", padx=10)

    def _build_settings_tab(self, parent: ctk.CTkFrame) -> None:
        panel = SettingsPanel(
            parent,
            store=self._settings_store,
            player=self._sound_player,
            initial_settings=self._settings,
            default_sound=DEFAULT_SOUND_PATH,
        )
        panel.pack(fill="both", expand=True, padx=5, pady=5)
        self._settings_panel = panel

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
            var.trace_add("write", lambda *_args, m="Tabata": self._update_mode_totals(m))
            self._entries["Tabata"][key] = var

        summary_frame = ctk.CTkFrame(parent, fg_color="transparent")
        summary_frame.grid(row=len(inputs), column=0, columnspan=2, padx=5, pady=(10, 5), sticky="w")

        hint = ctk.CTkLabel(
            summary_frame,
            text="Insert seconds or mm:ss (e.g. 1:30)",
            text_color="#A0A0A0",
        )
        hint.pack(anchor="w", pady=(0, 4))

        work_label = ctk.CTkLabel(summary_frame, text="Work total: 00:00")
        work_label.pack(anchor="w")
        rest_label = ctk.CTkLabel(summary_frame, text="Rest total: 00:00")
        rest_label.pack(anchor="w")

        self._total_labels["Tabata"] = {"work": work_label, "rest": rest_label}

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
            var.trace_add("write", lambda *_args, m="Boxing": self._update_mode_totals(m))
            self._entries["Boxing"][key] = var

        summary_frame = ctk.CTkFrame(parent, fg_color="transparent")
        summary_frame.grid(row=len(inputs), column=0, columnspan=2, padx=5, pady=(10, 5), sticky="w")

        hint = ctk.CTkLabel(
            summary_frame,
            text="Insert seconds or mm:ss (e.g. 3:00)",
            text_color="#A0A0A0",
        )
        hint.pack(anchor="w", pady=(0, 4))

        work_label = ctk.CTkLabel(summary_frame, text="Work total: 00:00")
        work_label.pack(anchor="w")
        rest_label = ctk.CTkLabel(summary_frame, text="Rest total: 00:00")
        rest_label.pack(anchor="w")

        self._total_labels["Boxing"] = {"work": work_label, "rest": rest_label}

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
        self._custom_text.bind("<<Modified>>", self._on_custom_modified)

        summary_frame = ctk.CTkFrame(parent, fg_color="transparent")
        summary_frame.grid(row=2, column=0, padx=5, pady=(10, 5), sticky="w")

        hint = ctk.CTkLabel(
            summary_frame,
            text="Intervals accept seconds or mm:ss per value",
            text_color="#A0A0A0",
        )
        hint.pack(anchor="w", pady=(0, 4))

        work_label = ctk.CTkLabel(summary_frame, text="Work total: 00:00")
        work_label.pack(anchor="w")
        rest_label = ctk.CTkLabel(summary_frame, text="Rest total: 00:00")
        rest_label.pack(anchor="w")

        self._total_labels["Custom"] = {"work": work_label, "rest": rest_label}

    def _on_custom_modified(self, event: object) -> None:
        widget = getattr(event, "widget", None)
        if widget is not None:
            try:
                widget.edit_modified(False)
            except Exception:
                pass
        self._update_mode_totals("Custom")

    def start_timer(self) -> None:
        if self._main_tabs.get() != "Timer":
            self._display_error("Switch to Timer tab to start")
            return

        try:
            phases = self._phases_for_selected_mode()
        except ValueError as error:
            self._display_error(str(error))
            return

        if not phases:
            self._display_error("Nothing to run")
            return

        if self._settings_panel is not None:
            self._settings = self._settings_panel.current_settings
            self._settings_panel.clear_status()
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
        self._after_id = None
        self._remaining -= 1
        if self._remaining >= 0:
            self._update_display()

        if self._remaining <= 0:
            self._sound_player.play()
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
        return TabataConfig(
            preparation=self._get_duration("Tabata", "preparation", "Preparation", allow_zero=True),
            work=self._get_duration("Tabata", "work", "Work", positive=True),
            rest=self._get_duration("Tabata", "rest", "Rest", allow_zero=True),
            rounds=self._get_int(self._entries["Tabata"]["rounds"], name="Rounds", positive=True),
            cycles=self._get_int(self._entries["Tabata"]["cycles"], name="Cycles", positive=True),
            cooldown=self._get_duration("Tabata", "cooldown", "Cooldown", allow_zero=True),
        )

    def _read_boxing_config(self) -> BoxingConfig:
        return BoxingConfig(
            work=self._get_duration("Boxing", "work", "Work", positive=True),
            rest=self._get_duration("Boxing", "rest", "Rest", allow_zero=True),
            rounds=self._get_int(self._entries["Boxing"]["rounds"], name="Rounds", positive=True),
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
                work = self._parse_duration_string(parts[0], f"Line {idx} work")
                rest_value = parts[1] if len(parts) == 2 else '0'
                rest = self._parse_duration_string(rest_value, f"Line {idx} rest")
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
            if work <= 0:
                raise ValueError(f"Line {idx}: work must be > 0")
            if rest < 0:
                raise ValueError(f"Line {idx}: rest must be >= 0")
            intervals.append((work, rest))

        if not intervals:
            raise ValueError("Provide at least one interval")

        return intervals

    def _update_mode_totals(self, mode: str | None = None) -> None:
        modes = [mode] if mode else list(self._total_labels.keys())
        for target in modes:
            phases = self._safe_phases_for_mode(target)
            self._apply_totals(target, phases)

    def _safe_phases_for_mode(self, mode: str) -> List[Phase] | None:
        try:
            if mode == "Tabata":
                config = self._read_tabata_config()
                return TabataTimer(config).phases
            if mode == "Boxing":
                config = self._read_boxing_config()
                return BoxingTimer(config).phases
            if mode == "Custom":
                if self._custom_text is None:
                    return None
                intervals = self._read_custom_intervals()
                return CustomTimer(intervals).phases
        except ValueError:
            return None
        return None

    def _apply_totals(self, mode: str, phases: List[Phase] | None) -> None:
        labels = self._total_labels.get(mode)
        if not labels:
            return
        if not phases:
            labels["work"].configure(text="Work total: --")
            labels["rest"].configure(text="Rest total: --")
            return
        work_seconds, rest_seconds = self._calculate_totals(phases)
        labels["work"].configure(
            text=f"Work total: {self._format_duration(work_seconds)}"
        )
        labels["rest"].configure(
            text=f"Rest total: {self._format_duration(rest_seconds)}"
        )

    @staticmethod
    def _calculate_totals(phases: Iterable[Phase]) -> tuple[int, int]:
        work = 0
        rest = 0
        for phase in phases:
            label = phase.label.lower()
            if label.startswith("work"):
                work += phase.duration
            elif label.startswith("rest"):
                rest += phase.duration
        return work, rest

    @staticmethod
    def _format_duration(seconds: int) -> str:
        if seconds <= 0:
            return "00:00"
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _get_duration(
        self,
        mode: str,
        key: str,
        name: str,
        *,
        positive: bool = False,
        allow_zero: bool = False,
    ) -> int:
        entries = self._entries.get(mode)
        if entries is None or key not in entries:
            raise ValueError(f"Missing entry for {mode}.{key}")
        raw = entries[key].get().strip()
        seconds = self._parse_duration_string(raw, name)
        if positive:
            if seconds <= 0:
                raise ValueError(f"{name} must be > 0")
            return seconds
        if allow_zero:
            if seconds < 0:
                raise ValueError(f"{name} must be >= 0")
            return seconds
        if seconds <= 0:
            raise ValueError(f"{name} must be > 0")
        return seconds

    @staticmethod
    def _parse_duration_string(raw: str, name: str) -> int:
        cleaned = raw.strip().lower()
        if not cleaned:
            raise ValueError(f"{name} must be provided")
        if ":" in cleaned:
            if cleaned.endswith("s") or cleaned.endswith("m"):
                raise ValueError(f"{name} must use mm:ss or seconds")
            parts = cleaned.split(":")
            if not all(part.isdigit() for part in parts):
                raise ValueError(f"{name} must use mm:ss or seconds")
            value = 0
            for part in parts:
                value = value * 60 + int(part)
            return value
        multiplier = 1
        if cleaned.endswith("m"):
            multiplier = 60
            cleaned = cleaned[:-1]
        elif cleaned.endswith("s"):
            cleaned = cleaned[:-1]
        if not cleaned or not cleaned.isdigit():
            raise ValueError(f"{name} must be a number of seconds or mm:ss")
        return int(cleaned) * multiplier

    def _get_int(
        self,
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
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Workout Timer with GUI (Tabata, Boxing, Custom, Settings) and optional CLI mode",
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
