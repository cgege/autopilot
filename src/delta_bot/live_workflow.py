from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

from .capture import ScreenCapture
from .config import BotConfig
from .input_control import InputController, Point


StatusCallback = Callable[[str], None]


def detect_mode_from_frame(frame: np.ndarray, sample_paths: dict[str, str | Path]) -> str | None:
    """Classify the lobby card from the fixed 2560x1440 sample region."""
    if frame is None or frame.size == 0:
        return None
    if frame.shape[:2] != (1440, 2560):
        frame = cv2.resize(frame, (2560, 1440), interpolation=cv2.INTER_AREA)
    region = cv2.cvtColor(frame[1030:1300, 1930:2490], cv2.COLOR_BGR2GRAY)
    best_mode: str | None = None
    best_score = -1.0
    for mode, path in sample_paths.items():
        sample = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if sample is None:
            continue
        template = cv2.cvtColor(sample[1030:1300, 1930:2490], cv2.COLOR_BGR2GRAY)
        if template.shape != region.shape:
            continue
        score = float(cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)[0, 0])
        if score > best_score:
            best_mode, best_score = mode, score
    return best_mode if best_score >= 0.55 else None


class LiveWorkflow:
    """Drive the visible lobby/loadout flow using configured 2560x1440 anchors."""

    def __init__(
        self,
        config: BotConfig,
        controller: InputController,
        status: StatusCallback | None = None,
        stop_event: threading.Event | None = None,
    ) -> None:
        self.config = config
        self.controller = controller
        self.capture = ScreenCapture(int(config.raw.get("capture", {}).get("monitor", 0)))
        self.status = status or (lambda _message: None)
        self.stop_event = stop_event or threading.Event()

    def _point(self, name: str, fallback: tuple[int, int]) -> Point:
        anchor = self.config.raw.get("ui_anchors", {}).get(name, {})
        if "x" in anchor and "y" in anchor:
            if "width" in anchor and "height" in anchor:
                return Point(int(anchor["x"]) + int(anchor["width"]) // 2,
                             int(anchor["y"]) + int(anchor["height"]) // 2)
            return Point(int(anchor["x"]), int(anchor["y"]))
        return Point(*fallback)

    def _wait(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.stop_event.is_set():
                raise InterruptedError("收到停止请求")
            time.sleep(0.05)

    def _click(self, label: str, point: Point) -> None:
        if self.stop_event.is_set():
            raise InterruptedError("收到停止请求")
        self.status(f"正在点击：{label}")
        self.controller.click(point)
        self._wait(0.8)

    def run(self, mode: str) -> None:
        loadout = self.config.loadout(self.config.raw["modes"][mode]["loadout"])
        backpack = str(loadout["backpack"])
        self.status(f"已选择{mode}，目标背包：{backpack}")

        self._click("配装", self._point("lobby_loadout_button", (2070, 1290)))
        self._click("背包槽", self._point("loadout_backpack_slot", (320, 910)))

        list_point = self._point("backpack_list", (320, 700))
        self.status("正在滚动背包列表")
        scroll_config = self.config.raw.get("workflow", {})
        rounds = int(scroll_config.get("backpack_scroll_rounds", 6))
        notches = int(scroll_config.get("backpack_scroll_notches", 12))
        for _ in range(max(1, rounds)):
            self.controller.scroll(-abs(notches), list_point)
            self._wait(0.25)
        self._wait(0.8)

        target_name = "backpack_target_confidential" if mode == "机密" else "backpack_target_classified"
        target_fallback = (320, 1050) if mode == "机密" else (320, 1210)
        self._click(backpack, self._point(target_name, target_fallback))
        purchase_name = "backpack_purchase_confidential" if mode == "机密" else "backpack_purchase_classified"
        purchase_fallback = (2250, 1145) if mode == "机密" else (2250, 1240)
        purchase_label = "购买"
        self._click(purchase_label, self._point(purchase_name, purchase_fallback))
        self._click("确认配装", self._point("confirm_loadout_button", (2250, 1265)))

        self.status("等待入局提醒")
        self._wait(2.0)
        self._click("仍要继续", self._point("entry_warning_continue_button", (1280, 940)))
        self.status("装备流程已完成，已提交入局")
