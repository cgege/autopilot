from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    width: int
    height: int


class ScreenCapture:
    """Capture the desktop and crop the configured game window."""

    def __init__(self, monitor: int = 0):
        self.monitor = monitor
        self._camera = None
        self._mss = None
        try:
            import dxcam  # type: ignore
            self._camera = dxcam.create(output_idx=monitor)
            LOGGER.info("capture backend=dxcam")
        except ImportError:
            from mss import mss  # type: ignore
            self._mss = mss()
            LOGGER.info("capture backend=mss")

    def grab(self, window: Rect | None = None) -> np.ndarray | None:
        if self._camera is not None:
            frame = self._camera.grab()
            if frame is None:
                return None
            image = np.asarray(frame)
        else:
            monitor = {
                "left": window.left if window else 0,
                "top": window.top if window else 0,
                "width": window.width if window else 1920,
                "height": window.height if window else 1080,
            }
            image = np.asarray(self._mss.grab(monitor))[:, :, :3]

        if window and self._camera is not None:
            image = image[window.top:window.top + window.height,
                          window.left:window.left + window.width]
        return image
