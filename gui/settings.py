"""Settings panel and audio utilities for Workout Timer GUI."""

from __future__ import annotations

import array
import json
import platform
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import customtkinter as ctk
from customtkinter import filedialog
import simpleaudio as sa


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
    """Plays the configured notification sound with graceful fallbacks."""

    def __init__(
        self,
        settings: SoundSettings,
        fallback_path: Path,
        *,
        on_fail: Callable[[], None] | None = None,
    ) -> None:
        self._fallback_path = fallback_path
        self._settings = settings
        self._on_fail = on_fail
        self._raw_data: bytes | None = None
        self._sample_width: int = 0
        self._channels: int = 0
        self._frame_rate: int = 0
        self._play_obj: sa.PlayObject | None = None
        self._active_path: Path | None = None
        self._afplay_path = (
            Path(shutil.which("afplay"))
            if platform.system() == "Darwin" and shutil.which("afplay")
            else None
        )
        self._load_wave(settings.sound_path)

    def update_settings(self, settings: SoundSettings) -> None:
        self._settings = settings
        self._load_wave(settings.sound_path)

    def play(self) -> None:
        if self._afplay_path and self._play_with_afplay():
            return

        if not self._raw_data:
            self._fallback()
            return

        volume = self._settings.normalized_volume()
        if volume <= 0.0:
            return

        data = self._apply_volume(volume)
        try:
            self._play_obj = sa.play_buffer(
                data, self._channels, self._sample_width, self._frame_rate
            )
        except Exception:
            self._fallback()

    def _fallback(self) -> None:
        if self._on_fail is not None:
            try:
                self._on_fail()
            except Exception:
                pass

    def _apply_volume(self, volume: float) -> bytes:
        raw = self._raw_data or b""
        if volume >= 0.999:
            return raw
        sample_width = self._sample_width
        if sample_width == 1:
            return self._scale_samples(raw, volume, 127, -128, "b")
        if sample_width == 2:
            return self._scale_samples(raw, volume, 32767, -32768, "h")
        return raw

    def _scale_samples(
        self,
        data: bytes,
        volume: float,
        max_val: int,
        min_val: int,
        typecode: str,
    ) -> bytes:
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
                    self._active_path = Path(candidate)
                    return
            except Exception:
                continue

        self._raw_data = None
        self._sample_width = 0
        self._channels = 0
        self._frame_rate = 0
        self._active_path = path if (self._afplay_path and path.exists()) else None

    def _play_with_afplay(self) -> bool:
        if self._afplay_path is None or self._active_path is None:
            return False
        volume = max(0.0, min(self._settings.normalized_volume(), 1.0))
        if volume <= 0.0:
            return True
        try:
            subprocess.Popen(
                [
                    str(self._afplay_path),
                    "-v",
                    f"{volume:.2f}",
                    str(self._active_path),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False


class SettingsPanel(ctk.CTkFrame):
    """Encapsulates the settings page UI and logic."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        store: SettingsStore,
        player: SoundPlayer,
        initial_settings: SoundSettings,
        default_sound: Path,
    ) -> None:
        super().__init__(master)
        self._store = store
        self._player = player
        self._default_sound = default_sound
        self._current_settings = initial_settings

        self._sound_path_var = ctk.StringVar(value=str(initial_settings.sound_path))
        self._volume_var = ctk.StringVar(
            value=f"{int(initial_settings.normalized_volume() * 100)}"
        )
        self._status_var = ctk.StringVar(value="")

        self._build()
        self._apply_volume_to_slider()

    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)

        sound_label = ctk.CTkLabel(self, text="Notification sound (WAV):")
        sound_label.grid(row=0, column=0, padx=5, pady=(15, 5), sticky="e")

        self._sound_entry = ctk.CTkEntry(self, textvariable=self._sound_path_var, width=240)
        self._sound_entry.grid(row=0, column=1, padx=5, pady=(15, 5), sticky="we")

        browse_button = ctk.CTkButton(self, text="Browse", command=self._browse, width=90)
        browse_button.grid(row=0, column=2, padx=5, pady=(15, 5))

        volume_label = ctk.CTkLabel(self, text="Volume (%)")
        volume_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        self._volume_slider = ctk.CTkSlider(
            self,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._on_volume_slider,
        )
        self._volume_slider.grid(row=1, column=1, padx=5, pady=5, sticky="we")

        self._volume_entry = ctk.CTkEntry(self, textvariable=self._volume_var, width=60)
        self._volume_entry.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self._volume_entry.bind("<FocusOut>", self._on_volume_entry)
        self._volume_entry.bind("<Return>", self._on_volume_entry)

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=(10, 5))

        reset_button = ctk.CTkButton(button_frame, text="Reset to Default", command=self._reset)
        reset_button.pack(side="left", padx=5)

        test_button = ctk.CTkButton(button_frame, text="Test Sound", command=self._test)
        test_button.pack(side="left", padx=5)

        save_button = ctk.CTkButton(button_frame, text="Save Settings", command=self._save)
        save_button.pack(side="left", padx=5)

        status_label = ctk.CTkLabel(self, textvariable=self._status_var, text_color="green")
        status_label.grid(row=3, column=0, columnspan=3, padx=5, pady=(5, 10), sticky="w")

    # Public API ---------------------------------------------------------

    def clear_status(self) -> None:
        self._status_var.set("")

    @property
    def current_settings(self) -> SoundSettings:
        return self._current_settings

    # Internal helpers ---------------------------------------------------

    def _apply_volume_to_slider(self) -> None:
        try:
            value = int(float(self._volume_var.get()))
        except ValueError:
            value = int(self._current_settings.normalized_volume() * 100)
        self._volume_slider.set(max(0, min(100, value)))

    def _browse(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select sound",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")],
        )
        if file_path:
            self._sound_path_var.set(file_path)
            self.clear_status()

    def _reset(self) -> None:
        self._sound_path_var.set(str(self._default_sound))
        self.clear_status()

    def _on_volume_slider(self, value: float) -> None:
        self._volume_var.set(f"{int(float(value))}")
        self.clear_status()

    def _on_volume_entry(self, _event: object) -> None:
        try:
            value = float(self._volume_var.get())
        except ValueError:
            value = self._current_settings.normalized_volume() * 100
        value = max(0.0, min(100.0, value))
        self._volume_var.set(f"{int(value)}")
        self._volume_slider.set(value)
        self.clear_status()

    def _gather(self) -> SoundSettings:
        sound_str = self._sound_path_var.get().strip() or str(self._default_sound)
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

    def _test(self) -> None:
        try:
            settings = self._gather()
        except ValueError as error:
            self._status_var.set(str(error))
            return
        self._player.update_settings(settings)
        self._player.play()
        self._status_var.set("Test sound played")

    def _save(self) -> None:
        try:
            settings = self._gather()
        except ValueError as error:
            self._status_var.set(str(error))
            return

        self._store.save(settings)
        self._player.update_settings(settings)
        self._current_settings = settings
        self._status_var.set("Settings saved")
