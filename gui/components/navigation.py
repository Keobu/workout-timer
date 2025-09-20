"""Navigation widgets for Workout Timer."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from PIL import Image
import customtkinter as ctk


class NavigationBar(ctk.CTkFrame):
    """Sidebar/topbar navigation that highlights the active mode."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        modes: Iterable[str],
        icons: dict[str, Path] | None = None,
        command: Callable[[str], None],
        orientation: str = "vertical",
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._command = command
        self._orientation = orientation
        self._active_palette = {
            "fg": "#1f6aa5",
            "text": "#FFFFFF",
            "inactive_text": "#A5B4C2",
            "border": "#1f6aa5",
        }
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._icons_cache: dict[str, ctk.CTkImage] = {}

        for mode in modes:
            icon = None
            if icons and mode in icons:
                path = icons[mode]
                image = Image.open(path)
                self._icons_cache[mode] = ctk.CTkImage(light_image=image, dark_image=image, size=(22, 22))
                icon = self._icons_cache[mode]
            btn = ctk.CTkButton(
                self,
                text=mode.title(),
                image=icon,
                compound="left",
                corner_radius=12,
                command=lambda m=mode: self._on_pressed(m),
                fg_color="transparent",
                hover_color="#1f6aa5",
                border_width=1,
                border_color=self._active_palette["border"],
                text_color=self._active_palette["inactive_text"],
            )
            self._buttons[mode] = btn
        self._active = next(iter(self._buttons)) if self._buttons else None
        self._render()

    def _render(self) -> None:
        for btn in self._buttons.values():
            btn.pack_forget()
        if self._orientation == "horizontal":
            for btn in self._buttons.values():
                btn.pack(side="left", padx=6, pady=4, ipady=2)
        else:
            for btn in self._buttons.values():
                btn.pack(fill="x", padx=6, pady=4, ipady=4)
        self._refresh_styles()

    def set_orientation(self, orientation: str) -> None:
        if orientation == self._orientation:
            return
        self._orientation = orientation
        self._render()

    def set_active(self, mode: str) -> None:
        if mode not in self._buttons:
            return
        self._active = mode
        self._refresh_styles()

    def _refresh_styles(self) -> None:
        for mode, btn in self._buttons.items():
            if mode == self._active:
                btn.configure(
                    fg_color=self._active_palette["fg"],
                    text_color=self._active_palette["text"],
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=self._active_palette["inactive_text"],
                )

    def apply_theme(self, appearance: str) -> None:
        if appearance == "light":
            self._active_palette = {
                "fg": "#0EA5E9",
                "text": "#0B1120",
                "inactive_text": "#475569",
                "border": "#0EA5E9",
            }
        else:
            self._active_palette = {
                "fg": "#1f6aa5",
                "text": "#FFFFFF",
                "inactive_text": "#A5B4C2",
                "border": "#1f6aa5",
            }
        for btn in self._buttons.values():
            btn.configure(border_color=self._active_palette["border"])
        self._refresh_styles()

    def _on_pressed(self, mode: str) -> None:
        self.set_active(mode)
        self._command(mode)
