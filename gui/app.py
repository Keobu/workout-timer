"""Main CustomTkinter application for Workout Timer."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Dict, List

import customtkinter as ctk

from gui.components.control_panel import ControlPanel
from gui.components.forms import BoxingForm, CustomForm, TabataForm, TopicsForm
from gui.components.navigation import NavigationBar
from gui.components.timer_display import TimerDisplay
from gui.settings import SettingsPanel, SettingsStore, SoundPlayer, SoundSettings
from gui.utils import format_seconds, summarize_phases
from timer.base import BoxingTimer, CustomTimer, Phase, TabataTimer

PHASE_COLOR_BG = {
    "idle": "#0B1220",
    "prep": "#2F2711",
    "work": "#0B2E1F",
    "rest": "#0D1F33",
    "cooldown": "#2C1212",
    "finish": "#271340",
}


class WorkoutTimerApp(ctk.CTk):
    MODES = ("tabata", "boxing", "custom", "topics", "settings")

    def __init__(self, *, base_dir: Path) -> None:
        super().__init__()
        self._base_dir = base_dir
        self._assets_dir = base_dir / "assets"
        self._sounds_dir = self._assets_dir / "sounds"
        self._icons_dir = self._assets_dir / "icons"
        self._history_path = base_dir / "history.json"

        self.title("Workout Timer")
        self.geometry("1180x760")
        self.minsize(820, 620)

        self._sound_defaults = {
            "prep": self._sounds_dir / "prep.wav",
            "work": self._sounds_dir / "work.wav",
            "rest": self._sounds_dir / "rest.wav",
            "cooldown": self._sounds_dir / "cooldown.wav",
            "finish": self._sounds_dir / "finish.wav",
        }

        self._settings_store = SettingsStore(base_dir / "settings.json", self._sound_defaults)
        self._settings: SoundSettings = self._settings_store.load()
        self._apply_theme(self._settings)

        self._sound_player = SoundPlayer(self._sound_defaults, self._settings, on_fail=self.bell)

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True)
        self._content.grid_columnconfigure(2, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        icons = {
            "tabata": self._icons_dir / "tabata.png",
            "boxing": self._icons_dir / "boxing.png",
            "custom": self._icons_dir / "custom.png",
            "topics": self._icons_dir / "topics.png",
            "settings": self._icons_dir / "settings.png",
        }
        self._nav = NavigationBar(
            self._content,
            modes=self.MODES,
            icons=icons,
            command=self._on_mode_change,
        )
        self._nav.apply_theme(self._settings.theme.lower())

        control_icons = {
            "start": self._icons_dir / "start.png",
            "stop": self._icons_dir / "stop.png",
            "reset": self._icons_dir / "reset.png",
        }

        self._timer_section = ctk.CTkFrame(self._content, fg_color="transparent")
        self._timer_display = TimerDisplay(self._timer_section)
        self._timer_display.pack(fill="both", expand=True, padx=12, pady=(12, 6))

        self._control_panel = ControlPanel(self._timer_section, icons=control_icons)
        self._control_panel.pack(fill="x", padx=12, pady=(6, 16))
        self._control_panel.bind("start", self._on_start)
        self._control_panel.bind("stop", self._on_stop)
        self._control_panel.bind("reset", self._on_reset)

        self._form_section = ctk.CTkFrame(self._content, fg_color="transparent")
        self._forms = {
            "tabata": TabataForm(self._form_section),
            "boxing": BoxingForm(self._form_section),
            "custom": CustomForm(self._form_section),
            "topics": TopicsForm(self._form_section),
        }
        for form in self._forms.values():
            form.bind_on_change(self._update_totals)

        self._summary_frame = ctk.CTkFrame(self._form_section, fg_color="#142033")
        self._summary_frame.pack(fill="x", padx=8, pady=8)
        self._work_total_label = ctk.CTkLabel(
            self._summary_frame,
            text="Work total: --",
            font=("SF Pro Text", 18, "bold"),
        )
        self._work_total_label.pack(anchor="w", padx=12, pady=(8, 4))
        self._rest_total_label = ctk.CTkLabel(
            self._summary_frame,
            text="Rest total: --",
            font=("SF Pro Text", 18),
        )
        self._rest_total_label.pack(anchor="w", padx=12, pady=(0, 4))
        self._session_length_label = ctk.CTkLabel(
            self._summary_frame,
            text="Session length: --",
            font=("SF Pro Text", 16),
            text_color="#9AA5B1",
        )
        self._session_length_label.pack(anchor="w", padx=12, pady=(0, 8))

        sound_library = list(self._sounds_dir.glob("*.wav"))
        self._settings_panel = SettingsPanel(
            self._form_section,
            store=self._settings_store,
            player=self._sound_player,
            initial_settings=self._settings,
            sound_library=sound_library,
            sound_defaults=self._sound_defaults,
            on_change=self._on_preferences_changed,
        )

        self._timer_display.set_font_scale(self._settings.font_scale)
        self._control_panel.set_font_scale(self._settings.font_scale)

        self._active_mode = "tabata"
        self._nav.set_active(self._active_mode)
        self._show_mode(self._active_mode)
        self._control_panel.set_state(running=False)

        self._phases: List[Phase] = []
        self._current_phase_index = -1
        self._remaining_seconds = 0
        self._after_id: str | None = None
        self._running = False
        self._paused = False
        self._session_started_at: dt.datetime | None = None
        self._session_summary: dict[str, int] = {}

        self.bind("<Configure>", self._on_resize)
        self._layout_orientation = "horizontal"
        self._apply_layout("horizontal")
        self._update_totals()
        self._apply_phase_theme("idle")

    # Layout -------------------------------------------------------------

    def _apply_layout(self, orientation: str) -> None:
        self._layout_orientation = orientation
        for widget in (self._nav, self._timer_section, self._form_section):
            widget.grid_forget()
        if orientation == "horizontal":
            self._content.grid_columnconfigure(0, weight=0, minsize=160)
            self._content.grid_columnconfigure(1, weight=1)
            self._content.grid_columnconfigure(2, weight=1)
            self._nav.set_orientation("vertical")
            self._control_panel.set_orientation("horizontal")
            self._nav.grid(row=0, column=0, sticky="nsw", padx=12, pady=16)
            self._timer_section.grid(row=0, column=1, sticky="nsew", padx=(8, 12), pady=16)
            self._form_section.grid(row=0, column=2, sticky="nsew", padx=(8, 16), pady=16)
        else:
            for col in range(3):
                self._content.grid_columnconfigure(col, weight=0)
            self._content.grid_columnconfigure(0, weight=1)
            self._content.grid_columnconfigure(1, weight=1)
            self._nav.set_orientation("horizontal")
            self._control_panel.set_orientation("vertical")
            self._nav.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(12, 6))
            self._timer_section.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=8)
            self._form_section.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=16, pady=(6, 16))

    def _on_resize(self, event: object) -> None:
        width = self.winfo_width()
        orientation = "horizontal" if width > 1000 else "vertical"
        if orientation != self._layout_orientation:
            self._apply_layout(orientation)

    # Mode management ----------------------------------------------------

    def _show_mode(self, mode: str) -> None:
        for widget in self._form_section.winfo_children():
            widget.pack_forget()
        if mode == "settings":
            self._timer_display.set_phase("idle", "Settings")
            self._timer_display.set_time("00:00")
            self._settings_panel.pack(fill="both", expand=True, padx=8, pady=8)
            self._summary_frame.pack_forget()
            self._control_panel.set_state(running=False)
        elif mode == "topics":
            self._timer_display.set_phase("idle", "Topics")
            self._timer_display.set_time("00:00")
            form = self._forms[mode]
            form.pack(fill="both", expand=True, padx=8, pady=8)
            self._summary_frame.pack_forget()
            self._settings_panel.pack_forget()
            self._control_panel.set_state(running=False)
        else:
            form = self._forms[mode]
            form.pack(fill="both", expand=True, padx=8, pady=8)
            self._summary_frame.pack(fill="x", padx=8, pady=8)
            self._settings_panel.pack_forget()
            self._update_totals()

    def _on_mode_change(self, mode: str) -> None:
        if self._running:
            return
        self._active_mode = mode
        self._nav.set_active(mode)
        self._show_mode(mode)

    # Timer control ------------------------------------------------------

    def _on_start(self) -> None:
        if self._active_mode in ("settings", "topics"):
            return
        if self._running:
            return
        if self._paused and self._phases:
            self._running = True
            self._schedule_tick()
            self._control_panel.set_state(running=True)
            return

        try:
            self._phases = self._build_phases()
        except ValueError as error:
            self._timer_display.set_phase("idle", str(error))
            return

        if not self._phases:
            self._timer_display.set_phase("idle", "Nothing to run")
            return

        summary = summarize_phases(self._phases)
        self._session_summary = summary
        self._session_summary["total"] = sum(summary.values())
        if self._active_mode == "tabata":
            tabata_form = self._forms["tabata"]
            config = tabata_form.get_config()
            self._session_summary["rounds"] = config.rounds * config.cycles
        elif self._active_mode == "boxing":
            boxing_form = self._forms["boxing"]
            config = boxing_form.get_config()
            self._session_summary["rounds"] = config.rounds
        else:
            custom_form = self._forms["custom"]
            intervals = custom_form.get_intervals()
            self._session_summary["rounds"] = len(intervals)

        self._session_started_at = dt.datetime.now(dt.timezone.utc)
        self._current_phase_index = 0
        self._paused = False
        self._running = True
        self._start_phase(self._current_phase_index)
        self._control_panel.set_state(running=True)

    def _on_stop(self) -> None:
        if not self._running:
            return
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self._running = False
        self._paused = True
        self._control_panel.set_state(running=False)

    def _on_reset(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self._running = False
        self._paused = False
        self._phases = []
        self._current_phase_index = -1
        self._remaining_seconds = 0
        self._timer_display.reset()
        self._apply_phase_theme("idle")
        self._control_panel.set_state(running=False)

    def _build_phases(self) -> List[Phase]:
        if self._active_mode == "tabata":
            form = self._forms["tabata"]
            config = form.get_config()
            return TabataTimer(config).phases
        if self._active_mode == "boxing":
            form = self._forms["boxing"]
            config = form.get_config()
            return BoxingTimer(config).phases
        form = self._forms["custom"]
        intervals = form.get_intervals()
        return CustomTimer(intervals).phases

    def _start_phase(self, index: int) -> None:
        if index >= len(self._phases):
            self._finish_session()
            return
        phase = self._phases[index]
        self._current_phase_index = index
        self._remaining_seconds = phase.duration
        self._timer_display.set_phase(phase.kind, phase.label)
        self._apply_phase_theme(phase.kind)
        self._sound_player.play(phase.kind)
        self._update_time_label()
        self._schedule_tick()

    def _schedule_tick(self) -> None:
        self._after_id = self.after(1000, self._tick)

    def _tick(self) -> None:
        self._after_id = None
        if not self._running:
            return
        self._remaining_seconds -= 1
        if self._remaining_seconds > 0:
            self._update_time_label()
            self._schedule_tick()
            return
        self._update_time_label()
        next_index = self._current_phase_index + 1
        if next_index >= len(self._phases):
            self._sound_player.play("finish")
            self._finish_session()
            return
        self._start_phase(next_index)

    def _update_time_label(self) -> None:
        time_str = format_seconds(self._remaining_seconds, include_hours=False)
        self._timer_display.set_time(time_str)

    def _finish_session(self) -> None:
        self._running = False
        self._paused = False
        self._control_panel.set_state(running=False)
        self._timer_display.set_phase("finish", "Completed!")
        self._apply_phase_theme("finish")
        self._show_summary_dialog()

    # Settings -----------------------------------------------------------

    def _apply_theme(self, settings: SoundSettings) -> None:
        appearance = settings.theme.lower()
        if appearance not in {"dark", "light", "system"}:
            appearance = "dark"
        ctk.set_appearance_mode(appearance)
        ctk.set_widget_scaling(max(0.8, min(settings.font_scale, 1.4)))
        if hasattr(self, "_nav"):
            self._nav.apply_theme(appearance)

    def _on_preferences_changed(self, settings: SoundSettings) -> None:
        self._settings = settings
        self._apply_theme(settings)
        self._sound_player.update_settings(settings)
        self._timer_display.set_font_scale(settings.font_scale)
        self._control_panel.set_font_scale(settings.font_scale)

    # Totals -------------------------------------------------------------

    def _update_totals(self) -> None:
        if self._active_mode in ("settings", "topics"):
            self._work_total_label.configure(text="Work total: --")
            self._rest_total_label.configure(text="Recovery total: --")
            self._session_length_label.configure(text="Session length: --")
            return
        try:
            phases = self._build_phases()
        except ValueError:
            self._work_total_label.configure(text="Work total: --")
            self._rest_total_label.configure(text="Recovery total: --")
            self._session_length_label.configure(text="Session length: --")
            return
        if not phases:
            self._work_total_label.configure(text="Work total: --")
            self._rest_total_label.configure(text="Recovery total: --")
            self._session_length_label.configure(text="Session length: --")
            return
        summary = summarize_phases(phases)
        self._work_total_label.configure(
            text=f"Work total: {format_seconds(summary['work'])}"
        )
        rest_seconds = summary.get("rest", 0) + summary.get("prep", 0) + summary.get("cooldown", 0)
        self._rest_total_label.configure(
            text=f"Recovery total: {format_seconds(rest_seconds)}"
        )
        total = sum(summary.values())
        self._session_length_label.configure(
            text=f"Session length: {format_seconds(total)}"
        )

    # Summary dialog -----------------------------------------------------

    def _show_summary_dialog(self) -> None:
        if not self._session_summary:
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Session Summary")
        dialog.geometry("420x320")
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=18, pady=18)

        header = ctk.CTkLabel(
            frame,
            text="Workout Completed",
            font=("SF Pro Display", 24, "bold"),
        )
        header.pack(pady=(8, 16))

        def row(label: str, value: str) -> None:
            row_frame = ctk.CTkFrame(frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(row_frame, text=label, anchor="w").pack(side="left")
            ctk.CTkLabel(row_frame, text=value, anchor="e").pack(side="right")

        row("Total work", format_seconds(self._session_summary.get("work", 0)))
        recovery = (
            self._session_summary.get("rest", 0)
            + self._session_summary.get("prep", 0)
            + self._session_summary.get("cooldown", 0)
        )
        row("Total recovery", format_seconds(recovery))
        row("Rounds completed", str(self._session_summary.get("rounds", 0)))
        row("Session length", format_seconds(self._session_summary.get("total", 0)))

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=6, pady=(18, 6))

        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save Session",
            command=lambda: self._save_history(save_btn, dialog),
        )
        save_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy).pack(side="right")

    def _save_history(self, button: ctk.CTkButton, dialog: ctk.CTkToplevel) -> None:
        record = {
            "mode": self._active_mode,
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "work_seconds": self._session_summary.get("work", 0),
            "prep_seconds": self._session_summary.get("prep", 0),
            "rest_seconds": self._session_summary.get("rest", 0),
            "cooldown_seconds": self._session_summary.get("cooldown", 0),
            "rounds_completed": self._session_summary.get("rounds", 0),
            "total_seconds": self._session_summary.get("total", 0),
        }
        try:
            history = json.loads(self._history_path.read_text()) if self._history_path.exists() else []
            history.append(record)
            self._history_path.write_text(json.dumps(history, indent=2))
            button.configure(state="disabled", text="Saved")
        except Exception:
            button.configure(text="Error saving")

    # Helpers ------------------------------------------------------------

    def _apply_phase_theme(self, phase: str) -> None:
        color = PHASE_COLOR_BG.get(phase, PHASE_COLOR_BG["idle"])
        self._content.configure(fg_color=color)


def run_app(base_dir: Path) -> None:
    app = WorkoutTimerApp(base_dir=base_dir)
    app.mainloop()
