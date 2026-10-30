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
        ctypes.windll.user32.keybd_event(virtual_key, 0, 0, 0)
        ctypes.windll.user32.keybd_event(virtual_key, 0, 2, 0)
