"""Entry point for the Workout Timer app with CLI, multi-mode GUI, and settings."""

from __future__ import annotations

import argparse
import array
import json
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import customtkinter as ctk
from customtkinter import filedialog
import simpleaudio as sa

from timer.base import (
    BoxingConfig,
    BoxingTimer,
    CountdownTimer,
    CustomTimer,
    Phase,
    TabataConfig,
    TabataTimer,
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SOUND_PATH = BASE_DIR / "assets" / "beep.wav"
SETTINGS_PATH = BASE_DIR / "settings.json"


@dataclass
class SoundSettings:
    """Configuration for notification audio."""

    sound_path: Path
    volume: float

    def normalized_volume(self) -> float:
        return max(0.0, min(self.volume, 1.0))


class SettingsStore:
    """Load and persist settings from/to disk."""

    def __init__(self, path: Path, default_sound: Path) -> None:
        self._path = path
        self._default_sound = default_sound

    def load(self) -> SoundSettings:
        if not self._path.exists():
            return SoundSettings(self._default_sound, 1.0)

        try:
            data = json.loads(self._path.read_text())
            sound_path = Path(data.get("sound_path", str(self._default_sound)))
            volume = float(data.get("volume", 1.0))
        except (OSError, ValueError, TypeError):
            return SoundSettings(self._default_sound, 1.0)

        return SoundSettings(sound_path, max(0.0, min(volume, 1.0)))

    def save(self, settings: SoundSettings) -> None:
        payload = {
            "sound_path": str(settings.sound_path),
            "volume": settings.normalized_volume(),
        }
        self._path.write_text(json.dumps(payload, indent=2))


class SoundPlayer:
    """Plays the configured notification sound."""

    def __init__(self, settings: SoundSettings, fallback_path: Path) -> None:
        self._fallback_path = fallback_path
        self._settings = settings
        self._raw_data: bytes | None = None
        self._sample_width: int = 0
        self._channels: int = 0
        self._frame_rate: int = 0
        self._load_wave(settings.sound_path)

    def update_settings(self, settings: SoundSettings) -> None:
        self._settings = settings
        self._load_wave(settings.sound_path)

    def play(self) -> None:
        if not self._raw_data:
            return
        volume = self._settings.normalized_volume()
        if volume <= 0.0:
            return
        data = self._apply_volume(volume)
        try:
            sa.play_buffer(data, self._channels, self._sample_width, self._frame_rate)
        except Exception:
            # Silently ignore playback failures to avoid breaking the timer loop.
            pass

    def _apply_volume(self, volume: float) -> bytes:
        raw = self._raw_data or b''
        if volume >= 0.999:
            return raw
        sample_width = self._sample_width
        if sample_width == 1:
            return self._scale_samples(raw, volume, 127, -128, 'b')
        if sample_width == 2:
            return self._scale_samples(raw, volume, 32767, -32768, 'h')
        return raw

    def _scale_samples(self, data: bytes, volume: float, max_val: int, min_val: int, typecode: str) -> bytes:
        arr = array.array(typecode)
        arr.frombytes(data)
        for idx, value in enumerate(arr):
            scaled = int(value * volume)
            if scaled > max_val:
                scaled = max_val
            elif scaled < min_val:
                scaled = min_val
            arr[idx] = scaled
        return arr.tobytes()

    def _load_wave(self, path: Path) -> None:
        candidate_paths = [path]
        if path != self._fallback_path:
            candidate_paths.append(self._fallback_path)

        for candidate in candidate_paths:
            try:
                with wave.open(str(candidate), "rb") as wav_file:
                    self._channels = wav_file.getnchannels()
                    self._sample_width = wav_file.getsampwidth()
                    self._frame_rate = wav_file.getframerate()
                    self._raw_data = wav_file.readframes(wav_file.getnframes())
                    return
            except Exception:
                continue

        self._raw_data = None
        self._sample_width = 0
        self._channels = 0
        self._frame_rate = 0


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
        self._custom_text: ctk.CTkTextbox | None = None

        self._settings_store = SettingsStore(SETTINGS_PATH, DEFAULT_SOUND_PATH)
        self._settings = self._settings_store.load()
        self._sound_player = SoundPlayer(self._settings, DEFAULT_SOUND_PATH)

        self._sound_path_var = ctk.StringVar(value=str(self._settings.sound_path))
        self._volume_var = ctk.StringVar(value=f"{int(self._settings.normalized_volume() * 100)}")
        self._settings_status_var = ctk.StringVar(value="")

        self._build_widgets()
        self._apply_volume_to_slider()

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
        parent.grid_columnconfigure(1, weight=1)

        sound_label = ctk.CTkLabel(parent, text="Notification sound (WAV):")
        sound_label.grid(row=0, column=0, padx=5, pady=(15, 5), sticky="e")

        self._sound_path_entry = ctk.CTkEntry(parent, textvariable=self._sound_path_var, width=240)
        self._sound_path_entry.grid(row=0, column=1, padx=5, pady=(15, 5), sticky="we")

        browse_button = ctk.CTkButton(parent, text="Browse", command=self._browse_sound_file, width=90)
        browse_button.grid(row=0, column=2, padx=5, pady=(15, 5))

        volume_label = ctk.CTkLabel(parent, text="Volume (%)")
        volume_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        self._volume_slider = ctk.CTkSlider(
            parent,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._on_volume_slider,
        )
        self._volume_slider.grid(row=1, column=1, padx=5, pady=5, sticky="we")

        self._volume_entry = ctk.CTkEntry(parent, textvariable=self._volume_var, width=60)
        self._volume_entry.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self._volume_entry.bind("<FocusOut>", self._on_volume_entry)
        self._volume_entry.bind("<Return>", self._on_volume_entry)

        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=(10, 5))

        reset_button = ctk.CTkButton(button_frame, text="Reset to Default", command=self._reset_sound_path)
        reset_button.pack(side="left", padx=5)

        test_button = ctk.CTkButton(button_frame, text="Test Sound", command=self._test_sound)
        test_button.pack(side="left", padx=5)

        save_button = ctk.CTkButton(button_frame, text="Save Settings", command=self._save_settings)
        save_button.pack(side="left", padx=5)

        status_label = ctk.CTkLabel(parent, textvariable=self._settings_status_var, text_color="green")
        status_label.grid(row=3, column=0, columnspan=3, padx=5, pady=(5, 10), sticky="w")

    def _apply_volume_to_slider(self) -> None:
        try:
            value = int(float(self._volume_var.get()))
        except ValueError:
            value = int(self._settings.normalized_volume() * 100)
        self._volume_slider.set(max(0, min(100, value)))

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

        self._settings_status_var.set("")
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

    def _browse_sound_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select sound",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")],
        )
        if file_path:
            self._sound_path_var.set(file_path)
            self._settings_status_var.set("")

    def _reset_sound_path(self) -> None:
        self._sound_path_var.set(str(DEFAULT_SOUND_PATH))
        self._settings_status_var.set("")

    def _on_volume_slider(self, value: float) -> None:
        self._volume_var.set(f"{int(float(value))}")
        self._settings_status_var.set("")

    def _on_volume_entry(self, _event: object) -> None:
        try:
            value = float(self._volume_var.get())
        except ValueError:
            value = self._settings.normalized_volume() * 100
        value = max(0.0, min(100.0, value))
        self._volume_var.set(f"{int(value)}")
        self._volume_slider.set(value)
        self._settings_status_var.set("")

    def _test_sound(self) -> None:
        try:
            settings = self._gather_settings()
        except ValueError as error:
            self._settings_status_var.set(str(error))
            return
        self._sound_player.update_settings(settings)
        self._sound_player.play()
        self._settings_status_var.set("Test sound played")

    def _save_settings(self) -> None:
        try:
            settings = self._gather_settings()
        except ValueError as error:
            self._settings_status_var.set(str(error))
            return

        self._settings_store.save(settings)
        self._settings = settings
        self._sound_player.update_settings(settings)
        self._settings_status_var.set("Settings saved")

    def _gather_settings(self) -> SoundSettings:
        sound_str = self._sound_path_var.get().strip() or str(DEFAULT_SOUND_PATH)
        sound_path = Path(sound_str).expanduser()
        if not sound_path.is_file():
            raise ValueError("Sound file not found")
        try:
            volume_percent = float(self._volume_var.get())
        except ValueError as exc:
            raise ValueError("Volume must be between 0 and 100") from exc
        if not 0.0 <= volume_percent <= 100.0:
            raise ValueError("Volume must be between 0 and 100")
        volume = volume_percent / 100.0
        return SoundSettings(sound_path, volume)

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
