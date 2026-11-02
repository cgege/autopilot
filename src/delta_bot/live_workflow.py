from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

from .capture import ScreenCapture
from .capture import Rect
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
        entry_warning_template: str | Path | None = None,
        in_match_template: str | Path | None = None,
        inventory_template: str | Path | None = None,
    ) -> None:
        self.config = config
        self.controller = controller
        self.capture = ScreenCapture(int(config.raw.get("capture", {}).get("monitor", 0)))
        self.status = status or (lambda _message: None)
        self.stop_event = stop_event or threading.Event()
        self.entry_warning_template = Path(entry_warning_template) if entry_warning_template else None
        self.in_match_template = Path(in_match_template) if in_match_template else None
        self.inventory_template = Path(inventory_template) if inventory_template else None

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

    def _grab(self) -> np.ndarray | None:
        capture = self.config.raw.get("capture", {})
        return self.capture.grab(Rect(
            0,
            0,
            int(capture.get("screen_width", 2560)),
            int(capture.get("screen_height", 1440)),
        ))

    def _template_visible(self, frame: np.ndarray, template_path: Path,
                          rect: tuple[int, int, int, int], threshold: float = 0.55) -> bool:
        sample = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
        if sample is None:
            return False
        left, top, width, height = rect
        if frame.shape[0] < top + height or frame.shape[1] < left + width:
            return False
        if sample.shape[0] < top + height or sample.shape[1] < left + width:
            return False
        template = cv2.cvtColor(sample[top:top + height, left:left + width], cv2.COLOR_BGR2GRAY)
        region = cv2.cvtColor(frame[top:top + height, left:left + width], cv2.COLOR_BGR2GRAY)
        if region.shape != template.shape:
            return False
        score = float(cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)[0, 0])
        return score >= threshold

    def _wait_for_entry_warning(self) -> None:
        if self.entry_warning_template is None:
            self._wait(float(self.config.raw.get("workflow", {}).get("entry_warning_wait_seconds", 8)))
            return
        workflow = self.config.raw.get("workflow", {})
        timeout = float(workflow.get("entry_warning_timeout_seconds", 180))
        self.status(f"等待入局提醒（最长 {int(timeout)} 秒）")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.stop_event.is_set():
                raise InterruptedError("收到停止请求")
            frame = self._grab()
            if frame is not None and self._template_visible(
                frame, self.entry_warning_template, (1060, 880, 440, 120)
            ):
                return
            time.sleep(0.5)
        raise TimeoutError("等待入局提醒超时，未执行继续操作")

    def _wait_for_in_match(self) -> None:
        if self.in_match_template is None:
            self._wait(8.0)
            return
        workflow = self.config.raw.get("workflow", {})
        timeout = float(workflow.get("in_match_timeout_seconds", 180))
        self.status(f"等待可操作 HUD（最长 {int(timeout)} 秒）")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.stop_event.is_set():
                raise InterruptedError("收到停止请求")
            frame = self._grab()
            if frame is not None and self._template_visible(
                frame, self.in_match_template, (1900, 1240, 620, 200), threshold=0.48
            ):
                return
            time.sleep(0.5)
        raise TimeoutError("等待可操作 HUD 超时，未执行人物操作")

    def _wait_for_inventory(self) -> None:
        workflow = self.config.raw.get("workflow", {})
        timeout = float(workflow.get("inventory_timeout_seconds", 10))
        template_path = self.inventory_template
        if template_path is None:
            self._wait(1.0)
            return
        self.status(f"等待装备界面（最长 {int(timeout)} 秒）")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.stop_event.is_set():
                raise InterruptedError("收到停止请求")
            frame = self._grab()
            if frame is not None and self._template_visible(
                frame, template_path, (960, 560, 650, 260), threshold=0.45
            ):
                return
            time.sleep(0.25)
        raise TimeoutError("装备界面识别超时，未执行丢包操作")

    def _drop_equipped_backpack(self, mode: str) -> None:
        if mode != "机密":
            self.status("当前模式跳过 GT5 背包丢弃")
            return
        workflow = self.config.raw.get("workflow", {})
        self.status("按 Tab 打开装备界面")
        self.controller.key(0x09)
        self._wait_for_inventory()
        target = self._point("inventory_target_confidential", (1075, 710))
        self.status("鼠标移到金色 GT5 野战背包")
        self.controller.move(target)
        self._wait(0.3)
        self.status("按 Alt+D 丢弃 GT5 野战背包")
        self.controller.hotkey(0x12, 0x44)
        self._wait(0.8)
        self.status("按 Tab 关闭装备界面")
        self.controller.key(0x09)
        self._wait(0.8)

    def _perform_first_action(self, mode: str) -> None:
        workflow = self.config.raw.get("workflow", {})
        settle_seconds = float(workflow.get("in_match_settle_seconds", 4))
        backward_seconds = float(workflow.get("backward_hold_seconds", 2))
        look_down_pixels = int(workflow.get("look_down_pixels", 700))
        look_down_seconds = float(workflow.get("look_down_seconds", 0.8))
        self.status(f"HUD 已出现，等待 {settle_seconds:g} 秒稳定")
        self._wait(settle_seconds)
        self._drop_equipped_backpack(mode)
        self.status(f"按住 S {backward_seconds:g} 秒")
        self.controller.hold_key(0x53, backward_seconds)
        self._wait(0.4)
        self.status("按 G 拿出道具")
        self.controller.key(0x47)
        self._wait(0.6)
        self.status("鼠标向下，视角对准脚下")
        self.controller.move_relative(0, look_down_pixels, look_down_seconds)
        self._wait(0.4)
        self.status("再次按 G 丢出道具")
        self.controller.key(0x47)

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

        self._click("出发", self._point("lobby_depart_button", (2320, 1290)))
        self._wait_for_entry_warning()
        self._click("仍要继续", self._point("entry_warning_continue_button", (1280, 940)))
        self._wait_for_in_match()
        self._perform_first_action(mode)
        self.status("首个入局动作已完成")
