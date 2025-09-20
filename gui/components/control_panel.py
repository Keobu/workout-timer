"""Control panel with action buttons."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict

from PIL import Image
import customtkinter as ctk


class ControlPanel(ctk.CTkFrame):
    """Provides Start/Stop/Reset controls with icons."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        icons: Dict[str, Path],
        orientation: str = "horizontal",
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._orientation = orientation
        self._images: Dict[str, ctk.CTkImage] = {}
        self._buttons: Dict[str, ctk.CTkButton] = {}
        self._callbacks: Dict[str, Callable[[], None]] = {}

        config = {
            "start": {"text": "Start", "fg_color": "#10B981"},
            "stop": {"text": "Stop", "fg_color": "#EF4444"},
            "reset": {"text": "Reset", "fg_color": "#3B82F6"},
        }

        for key, meta in config.items():
            image = None
            if key in icons:
                pil = Image.open(icons[key])
                self._images[key] = ctk.CTkImage(light_image=pil, dark_image=pil, size=(28, 28))
                image = self._images[key]
            btn = ctk.CTkButton(
                self,
                text=meta["text"],
                image=image,
                compound="left",
                corner_radius=16,
                height=54,
                width=150,
                font=("SF Pro Display", 20, "bold"),
                fg_color=meta["fg_color"],
                hover_color="#1F2937",
                command=lambda k=key: self._fire(k),
            )
            self._buttons[key] = btn
        self._layout_buttons()

    def _layout_buttons(self) -> None:
        for btn in self._buttons.values():
            btn.pack_forget()
        if self._orientation == "vertical":
            for btn in self._buttons.values():
                btn.pack(fill="x", pady=8, padx=4)
        else:
            for btn in self._buttons.values():
                btn.pack(side="left", expand=True, padx=8, pady=6)

    def set_orientation(self, orientation: str) -> None:
        if orientation == self._orientation:
            return
        self._orientation = orientation
        self._layout_buttons()

    def bind(self, action: str, callback: Callable[[], None]) -> None:
        self._callbacks[action] = callback

    def set_state(self, *, running: bool) -> None:
        self._buttons["start"].configure(state="disabled" if running else "normal")
        self._buttons["stop"].configure(state="normal" if running else "disabled")
        self._buttons["reset"].configure(state="normal")

    def set_font_scale(self, scale: float) -> None:
        size = max(int(20 * scale), 14)
        for btn in self._buttons.values():
            btn.configure(font=("SF Pro Display", size, "bold"), height=int(54 * scale))

    def _fire(self, action: str) -> None:
        callback = self._callbacks.get(action)
        if callback:
            callback()
