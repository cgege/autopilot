from __future__ import annotations

import ctypes
import logging
import time
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Point:
    x: int
    y: int


class InputController:
    """Visible Windows input with a dry-run guard."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def move(self, point: Point, duration: float = 0.08) -> None:
        LOGGER.info("move x=%s y=%s dry_run=%s", point.x, point.y, self.dry_run)
        if not self.dry_run:
            ctypes.windll.user32.SetCursorPos(point.x, point.y)
        time.sleep(duration)

    def click(self, point: Point, button: str = "left") -> None:
        self.move(point)
        LOGGER.info("click button=%s dry_run=%s", button, self.dry_run)
        if self.dry_run:
            return
        if button == "left":
            down, up = 0x0002, 0x0004
        elif button == "right":
            down, up = 0x0008, 0x0010
        else:
            raise ValueError(f"Unsupported mouse button: {button}")
        ctypes.windll.user32.mouse_event(down, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)

    def key(self, virtual_key: int) -> None:
        LOGGER.info("key vk=%s dry_run=%s", virtual_key, self.dry_run)
        if self.dry_run:
            return
        self.key_down(virtual_key)
        self.key_up(virtual_key)

    def hotkey(self, modifier: int, virtual_key: int) -> None:
        """Press a two-key shortcut such as Alt+D."""
        LOGGER.info("hotkey modifier=%s key=%s dry_run=%s",
                    modifier, virtual_key, self.dry_run)
        self.key_down(modifier)
        try:
            self.key(virtual_key)
        finally:
            self.key_up(modifier)

    def key_down(self, virtual_key: int) -> None:
        LOGGER.info("key_down vk=%s dry_run=%s", virtual_key, self.dry_run)
        if not self.dry_run:
            ctypes.windll.user32.keybd_event(virtual_key, 0, 0, 0)

    def key_up(self, virtual_key: int) -> None:
        LOGGER.info("key_up vk=%s dry_run=%s", virtual_key, self.dry_run)
        if not self.dry_run:
            ctypes.windll.user32.keybd_event(virtual_key, 0, 2, 0)

    def hold_key(self, virtual_key: int, seconds: float) -> None:
        """Hold a key for a visible duration, including in dry-run timing."""
        self.key_down(virtual_key)
        try:
            time.sleep(max(0.0, seconds))
        finally:
            self.key_up(virtual_key)

    def move_relative(self, dx: int, dy: int, duration: float = 0.5) -> None:
        """Move the mouse relative to its current position."""
        LOGGER.info("move_relative dx=%s dy=%s duration=%s dry_run=%s",
                    dx, dy, duration, self.dry_run)
        if self.dry_run:
            time.sleep(max(0.0, duration))
            return
        steps = max(1, int(duration / 0.02))
        step_x = dx / steps
        step_y = dy / steps
        for index in range(steps):
            current_x = round(step_x * (index + 1)) - round(step_x * index)
            current_y = round(step_y * (index + 1)) - round(step_y * index)
            ctypes.windll.user32.mouse_event(0x0001, current_x, current_y, 0, 0)
            time.sleep(duration / steps)

    def scroll(self, clicks: int, point: Point | None = None) -> None:
        """Scroll the visible window; positive values move up, negative down."""
        if point is not None:
            self.move(point, duration=0.02)
        LOGGER.info("scroll clicks=%s dry_run=%s", clicks, self.dry_run)
        if not self.dry_run:
            ctypes.windll.user32.mouse_event(0x0800, 0, 0, int(clicks) * 120, 0)
