from __future__ import annotations

import ctypes
import sys
import threading
from pathlib import Path
from ctypes import wintypes

from .config import load_config
from .input_control import InputController
from .live_workflow import LiveWorkflow, detect_mode_from_frame
from .workflow import Workflow
from .capture import Rect, ScreenCapture


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM)
ENUMWINDOWSPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.LoadCursorW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.LoadCursorW.restype = ctypes.c_void_p
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
user32.SetWindowTextW.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [ENUMWINDOWSPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = ctypes.c_void_p

WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_SETFONT = 0x0030
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
BS_PUSHBUTTON = 0x00000000
CW_USEDEFAULT = 0x80000000

BUTTON_CONFIDENTIAL = 1001
BUTTON_CLASSIFIED = 1002
BUTTON_TOGGLE = 1003
BUTTON_AUTO = 1004
STATUS_ID = 1100


def bundled_path(relative: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / relative


class NativeApp:
    def __init__(self) -> None:
        self.instance = kernel32.GetModuleHandleW(None)
        self.hwnd: wintypes.HWND | None = None
        self.status: wintypes.HWND | None = None
        self.toggle_button: wintypes.HWND | None = None
        self.running = False
        self.last_mode: str | None = None
        self.last_value: int | None = None
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.proc = WNDPROC(self.window_proc)

    def create(self) -> None:
        class_name = "DeltaScreenBotNativeWindow"
        wnd_class = WNDCLASSW()
        wnd_class.lpfnWndProc = self.proc
        wnd_class.hInstance = self.instance
        wnd_class.lpszClassName = class_name
        wnd_class.hCursor = user32.LoadCursorW(None, ctypes.c_void_p(32512))
        wnd_class.hbrBackground = ctypes.c_void_p(6)
        user32.RegisterClassW(ctypes.byref(wnd_class))
        self.hwnd = user32.CreateWindowExW(
            0, class_name, "DeltaScreenBot 测试版", WS_OVERLAPPEDWINDOW | WS_VISIBLE,
            CW_USEDEFAULT, CW_USEDEFAULT, 700, 330, None, None, self.instance, None
        )
        self.add_controls()

    def add_controls(self) -> None:
        static_style = WS_CHILD | WS_VISIBLE
        button_style = WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON
        user32.CreateWindowExW(0, "STATIC", "当前版本：屏幕识别与配装流程", static_style,
                               30, 25, 600, 30, self.hwnd, None, self.instance, None)
        user32.CreateWindowExW(0, "STATIC", "开始机密流程：", static_style,
                               30, 80, 160, 30, self.hwnd, None, self.instance, None)
        user32.CreateWindowExW(0, "BUTTON", "机密（190000）", button_style,
                               210, 74, 180, 42, self.hwnd, ctypes.c_void_p(BUTTON_CONFIDENTIAL), self.instance, None)
        user32.CreateWindowExW(0, "STATIC", "开始绝密流程：", static_style,
                               30, 140, 160, 30, self.hwnd, None, self.instance, None)
        user32.CreateWindowExW(0, "BUTTON", "绝密（600000）", button_style,
                               210, 134, 180, 42, self.hwnd, ctypes.c_void_p(BUTTON_CLASSIFIED), self.instance, None)
        self.toggle_button = user32.CreateWindowExW(
            0, "BUTTON", "开始", button_style,
            420, 104, 150, 42, self.hwnd, ctypes.c_void_p(BUTTON_TOGGLE), self.instance, None
        )
        user32.CreateWindowExW(
            0, "BUTTON", "自动识别开始", button_style,
            420, 164, 150, 42, self.hwnd, ctypes.c_void_p(BUTTON_AUTO), self.instance, None
        )
        self.status = user32.CreateWindowExW(0, "STATIC", "状态：就绪", static_style,
                                             30, 215, 600, 50, self.hwnd, ctypes.c_void_p(STATUS_ID), self.instance, None)

    def set_status(self, text: str) -> None:
        if self.status:
            user32.SetWindowTextW(self.status, text)

    def set_toggle_label(self, text: str) -> None:
        if self.toggle_button:
            user32.SetWindowTextW(self.toggle_button, text)

    def focus_game(self, configured_title: str) -> bool:
        titles = [configured_title, "三角洲行动", "Delta Force"]
        titles = [title.casefold() for title in titles if title and title != "TARGET_GAME_WINDOW"]
        found: list[wintypes.HWND] = []

        @ENUMWINDOWSPROC
        def visit(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            buffer = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buffer, len(buffer))
            title = buffer.value.casefold()
            if title and any(candidate in title for candidate in titles):
                found.append(hwnd)
                return False
            return True

        user32.EnumWindows(visit, 0)
        if not found:
            return False
        user32.ShowWindow(found[0], 5)
        user32.SetForegroundWindow(found[0])
        return True

    def start(self, mode: str, value: int) -> None:
        if self.running or (self.worker and self.worker.is_alive()):
            return
        self.last_mode = mode
        self.last_value = value
        self.running = True
        self.stop_event.clear()
        self.set_toggle_label("停止")
        self.set_status(f"状态：正在准备{mode}方案…")
        self.worker = threading.Thread(target=self.run_live, args=(mode, value), daemon=True)
        self.worker.start()

    def run_live(self, mode: str, value: int) -> None:
        try:
            config = load_config(bundled_path("config/loadouts.yaml"))
            if not self.focus_game(config.window_title):
                raise RuntimeError("未找到游戏窗口；请将 window_title 配置为游戏标题")
            Workflow(config, InputController(dry_run=False)).plan_from_detected_mode(mode, value)
            LiveWorkflow(
                config,
                InputController(dry_run=False),
                status=lambda message: self.set_status(f"状态：{message}"),
                stop_event=self.stop_event,
            ).run(mode)
        except InterruptedError:
            self.set_status("状态：已停止")
        except Exception as exc:
            self.set_status(f"状态：错误：{exc}")
        finally:
            self.running = False
            self.set_toggle_label("开始")

    def auto_start(self) -> None:
        if self.running:
            return
        self.set_status("状态：正在识别大厅模式…")
        try:
            config = load_config(bundled_path("config/loadouts.yaml"))
            if not self.focus_game(config.window_title):
                self.set_status("状态：未找到游戏窗口；请将 window_title 配置为游戏标题")
                return
            capture_config = config.raw.get("capture", {})
            frame = ScreenCapture(int(capture_config.get("monitor", 0))).grab(
                Rect(0, 0, int(capture_config.get("screen_width", 2560)),
                     int(capture_config.get("screen_height", 1440)))
            )
            mode = detect_mode_from_frame(frame, {
                "机密": bundled_path("imgtest/1.jpg"),
                "绝密": bundled_path("imgtest/2.jpg"),
            })
            if mode is None:
                self.set_status("状态：未识别到机密/绝密大厅，请点击对应模式按钮")
                return
            value = int(config.raw["modes"][mode]["minimum_equipment_value"])
            self.start(mode, value)
        except Exception as exc:
            self.set_status(f"状态：识别错误：{exc}")

    def stop(self) -> None:
        if not self.running:
            return
        self.stop_event.set()
        self.set_toggle_label("停止中")
        self.set_status("状态：正在停止")

    def toggle(self) -> None:
        if self.running:
            self.stop()
            return
        if self.last_mode is None or self.last_value is None:
            self.set_status("状态：请选择机密或绝密后再开始")
            return
        self.start(self.last_mode, self.last_value)

    def window_proc(self, hwnd, message, wparam, lparam):
        if message == WM_COMMAND:
            control_id = int(wparam) & 0xFFFF
            notification_code = (int(wparam) >> 16) & 0xFFFF
            if notification_code != 0:
                return 0
            if control_id == BUTTON_CONFIDENTIAL:
                self.start("机密", 190000)
            elif control_id == BUTTON_CLASSIFIED:
                self.start("绝密", 600000)
            elif control_id == BUTTON_TOGGLE:
                if self.running:
                    self.stop()
                else:
                    self.toggle()
            elif control_id == BUTTON_AUTO:
                self.auto_start()
            return 0
        if message == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def run(self) -> None:
        self.create()
        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))


def main() -> None:
    NativeApp().run()


if __name__ == "__main__":
    main()
