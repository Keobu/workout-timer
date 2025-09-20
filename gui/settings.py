"""Settings management and sound handling for Workout Timer."""

from __future__ import annotations

import array
import json
import platform
import shutil
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable

import customtkinter as ctk
from customtkinter import filedialog
import simpleaudio as sa


_PHASES = ["prep", "work", "rest", "cooldown", "finish"]


@dataclass
class SoundSettings:
    theme: str = "Dark"
    font_scale: float = 1.0
    volume: float = 0.8
    phase_sounds: Dict[str, str] = field(default_factory=dict)

    def normalized_volume(self) -> float:
        return max(0.0, min(self.volume, 1.0))

    def as_dict(self) -> dict:
        return {
            "theme": self.theme,
            "font_scale": self.font_scale,
            "volume": self.normalized_volume(),
            "phase_sounds": self.phase_sounds,
        }

    @classmethod
    def from_dict(cls, data: dict, defaults: Dict[str, Path]) -> "SoundSettings":
        volume = float(data.get("volume", 0.8))
        theme = data.get("theme", "Dark")
        font_scale = float(data.get("font_scale", 1.0))
        stored = data.get("phase_sounds", {})
        phase_sounds: Dict[str, str] = {}
        for phase, default_path in defaults.items():
            phase_sounds[phase] = stored.get(phase, str(default_path))
        return cls(theme=theme, font_scale=font_scale, volume=volume, phase_sounds=phase_sounds)


class SettingsStore:
    def __init__(self, path: Path, sound_defaults: Dict[str, Path]) -> None:
        self._path = path
        self._defaults = sound_defaults

    def load(self) -> SoundSettings:
        if not self._path.exists():
            return SoundSettings.from_dict({}, self._defaults)
        try:
            data = json.loads(self._path.read_text())
        except (OSError, json.JSONDecodeError):
            return SoundSettings.from_dict({}, self._defaults)
        return SoundSettings.from_dict(data, self._defaults)

    def save(self, settings: SoundSettings) -> None:
        payload = settings.as_dict()
        self._path.write_text(json.dumps(payload, indent=2))


class SoundPlayer:
    """Handles playback with per-phase audio and graceful fallbacks."""

    def __init__(
        self,
        defaults: Dict[str, Path],
        settings: SoundSettings,
        *,
        on_fail: Callable[[], None] | None = None,
    ) -> None:
        self._defaults = defaults
        self._on_fail = on_fail
        self._settings = settings
        self._cache: Dict[Path, bytes] = {}
        self._metadata: Dict[Path, tuple[int, int, int]] = {}
        self._afplay_path = (
            Path(shutil.which("afplay"))
            if platform.system() == "Darwin" and shutil.which("afplay")
            else None
        )
        self.update_settings(settings)

    def update_settings(self, settings: SoundSettings) -> None:
        self._settings = settings
        self._load_all()

    def play(self, phase: str, *, override_path: Path | None = None) -> None:
        path = override_path or Path(self._settings.phase_sounds.get(phase, ""))
        if not path or not path.is_file():
            path = self._defaults.get(phase)
        if not path:
            return
        if self._afplay_path and self._play_with_afplay(path):
            return
        raw = self._cache.get(path)
        meta = self._metadata.get(path)
        if not raw or not meta:
            self._fallback()
            return
        volume = self._settings.normalized_volume()
        if volume <= 0.0:
            return
        channels, sample_width, frame_rate = meta
        data = self._apply_volume(raw, sample_width, volume)
        try:
            sa.play_buffer(data, channels, sample_width, frame_rate)
        except Exception:
            self._fallback()

    # Internal helpers ---------------------------------------------------

    def _load_all(self) -> None:
        self._cache.clear()
        self._metadata.clear()
        selected = {
            Path(p)
            for p in self._settings.phase_sounds.values()
            if p and Path(p).suffix.lower() == ".wav"
        }
        paths = selected | set(self._defaults.values())
        for path in paths:
            if not path or not path.is_file():
                continue
            try:
                with wave.open(str(path), "rb") as wav_file:
                    channels = wav_file.getnchannels()
                    sample_width = wav_file.getsampwidth()
                    frame_rate = wav_file.getframerate()
                    raw = wav_file.readframes(wav_file.getnframes())
            except Exception:
                continue
            self._cache[path] = raw
            self._metadata[path] = (channels, sample_width, frame_rate)

    def _apply_volume(self, raw: bytes, sample_width: int, volume: float) -> bytes:
        if volume >= 0.999:
            return raw
        if sample_width not in (1, 2):
            return raw
        typecode = "b" if sample_width == 1 else "h"
        max_val = 127 if sample_width == 1 else 32767
        min_val = -128 if sample_width == 1 else -32768
        arr = array.array(typecode)
        arr.frombytes(raw)
        for idx, value in enumerate(arr):
            scaled = int(value * volume)
            if scaled > max_val:
                scaled = max_val
            elif scaled < min_val:
                scaled = min_val
            arr[idx] = scaled
        return arr.tobytes()

    def _play_with_afplay(self, path: Path) -> bool:
        if self._afplay_path is None:
            return False
        volume = self._settings.normalized_volume()
        if volume <= 0.0:
            return True
        try:
            subprocess.Popen(
                [
                    str(self._afplay_path),
                    "-v",
                    f"{volume:.2f}",
                    str(path),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False

    def _fallback(self) -> None:
        if self._on_fail is not None:
            try:
                self._on_fail()
            except Exception:
                pass


class SettingsPanel(ctk.CTkFrame):
    """Interactive settings page with auto-saving preferences."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        store: SettingsStore,
        player: SoundPlayer,
        initial_settings: SoundSettings,
        sound_library: Iterable[Path],
        sound_defaults: Dict[str, Path],
        on_change: Callable[[SoundSettings], None],
    ) -> None:
        super().__init__(master)
        self._store = store
        self._player = player
        self._on_change = on_change
        self._settings = initial_settings
        self._pending_after: str | None = None
        self._defaults = sound_defaults

        self._sound_options = self._build_sound_options(sound_library)
        self._phase_vars: Dict[str, ctk.StringVar] = {}
        self._menus: Dict[str, ctk.CTkOptionMenu] = {}

        self._status_var = ctk.StringVar(master=self, value="")
        self._theme_var = ctk.StringVar(master=self, value=self._settings.theme)
        self._font_var = ctk.DoubleVar(master=self, value=self._settings.font_scale)
        self._volume_var = ctk.DoubleVar(master=self, value=self._settings.volume * 100)

        self._build()

    def _build_sound_options(self, library: Iterable[Path]) -> Dict[str, Path]:
        options: Dict[str, Path] = {}
        for path in list(library):
            options[path.stem.replace("_", " ").title()] = path
        for default_path in self._defaults.values():
            if default_path not in options.values():
                options[default_path.stem.replace("_", " ").title()] = default_path
        return dict(sorted(options.items()))

    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)

        theme_label = ctk.CTkLabel(self, text="Theme")
        theme_label.grid(row=0, column=0, padx=8, pady=(16, 8), sticky="e")

        theme_menu = ctk.CTkOptionMenu(
            self,
            values=["Dark", "Light", "System"],
            variable=self._theme_var,
            command=lambda _v: self._commit(),
        )
        theme_menu.grid(row=0, column=1, padx=8, pady=(16, 8), sticky="w")

        font_label = ctk.CTkLabel(self, text="Font Size")
        font_label.grid(row=1, column=0, padx=8, pady=8, sticky="e")
        font_slider = ctk.CTkSlider(
            self,
            from_=0.8,
            to=1.3,
            number_of_steps=10,
            variable=self._font_var,
            command=lambda _v: self._commit_delayed(),
        )
        font_slider.grid(row=1, column=1, padx=8, pady=8, sticky="we")

        volume_label = ctk.CTkLabel(self, text="Volume (%)")
        volume_label.grid(row=2, column=0, padx=8, pady=8, sticky="e")
        volume_slider = ctk.CTkSlider(
            self,
            from_=0,
            to=100,
            number_of_steps=100,
            variable=self._volume_var,
            command=lambda _v: self._commit_delayed(),
        )
        volume_slider.grid(row=2, column=1, padx=8, pady=8, sticky="we")

        row = 3
        for phase in _PHASES:
            display = phase.title()
            selected = self._display_name_for_path(Path(self._settings.phase_sounds.get(phase, "")))
            var = ctk.StringVar(master=self, value=selected)
            self._phase_vars[phase] = var
            label = ctk.CTkLabel(self, text=f"{display} Sound")
            label.grid(row=row, column=0, padx=8, pady=8, sticky="e")
            menu = ctk.CTkOptionMenu(
                self,
                variable=var,
                values=list(self._sound_options.keys()) + ["Browse…"],
                command=lambda value, phase=phase: self._on_sound_changed(phase, value),
                width=200,
            )
            menu.grid(row=row, column=1, padx=8, pady=8, sticky="w")
            self._menus[phase] = menu

            play_button = ctk.CTkButton(
                self,
                text="▶",
                width=36,
                command=lambda p=phase: self._play_phase_preview(p),
            )
            play_button.grid(row=row, column=2, padx=8, pady=8, sticky="w")
            row += 1

        status_label = ctk.CTkLabel(self, textvariable=self._status_var, text_color="#7DD3FC")
        status_label.grid(row=row, column=0, columnspan=3, padx=8, pady=(12, 6), sticky="w")

        add_button = ctk.CTkButton(self, text="Add Custom Sound", command=self._browse_custom)
        add_button.grid(row=row + 1, column=0, columnspan=3, padx=8, pady=(6, 16), sticky="we")

    # Event handlers -----------------------------------------------------

    def _display_name_for_path(self, path: Path | None) -> str:
        if path is None:
            return "--"
        for name, option_path in self._sound_options.items():
            if option_path == path:
                return name
        return path.stem.title()

    def _on_sound_changed(self, phase: str, name: str) -> None:
        if name == "Browse…":
            file_path = filedialog.askopenfilename(
                title="Select WAV",
                filetypes=[("WAV files", "*.wav")],
            )
            if not file_path:
                return
            path = Path(file_path)
            display_name = path.stem.replace("_", " ").title()
            self._sound_options[display_name] = path
            self._phase_vars[phase].set(display_name)
        else:
            path = self._sound_options[name]
            self._phase_vars[phase].set(name)
        self._refresh_menus()
        self._commit()

    def _play_phase_preview(self, phase: str) -> None:
        display = self._phase_vars[phase].get()
        path = self._sound_options.get(display) or self._defaults.get(phase)
        self._player.play(phase, override_path=path if path and path.is_file() else None)

    def _browse_custom(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Add custom WAV",
            filetypes=[("WAV files", "*.wav")],
        )
        if not file_path:
            return
        path = Path(file_path)
        display_name = path.stem.replace("_", " ").title()
        self._sound_options[display_name] = path
        # Do not assign automatically; user can choose from dropdowns
        self._status_var.set(f"Added {display_name}")
        self._refresh_menus()

    def _commit_delayed(self) -> None:
        if self._pending_after is not None:
            try:
                self.after_cancel(self._pending_after)
            except Exception:
                pass
        self._pending_after = self.after(350, self._commit)

    def _commit(self) -> None:
        self._pending_after = None
        settings = SoundSettings(
            theme=self._theme_var.get(),
            font_scale=float(self._font_var.get()),
            volume=float(self._volume_var.get()) / 100.0,
            phase_sounds={
                phase: str(self._sound_options.get(self._phase_vars[phase].get(), self._defaults.get(phase, "")))
                for phase in _PHASES
            },
        )
        self._settings = settings
        self._store.save(settings)
        self._status_var.set("Preferences saved")
        self._on_change(settings)

    def _refresh_menus(self) -> None:
        values = list(self._sound_options.keys()) + ["Browse…"]
        for menu in self._menus.values():
            menu.configure(values=values)
