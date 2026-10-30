from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from ctypes import wintypes

from .config import load_config
from .input_control import InputController
from .workflow import Workflow


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM)


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
BUTTON_STOP = 1003
STATUS_ID = 1100


def bundled_path(relative: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / relative


class NativeApp:
    def __init__(self) -> None:
        self.instance = kernel32.GetModuleHandleW(None)
        self.hwnd: wintypes.HWND | None = None
        self.status: wintypes.HWND | None = None
        self.proc = WNDPROC(self.window_proc)

    def create(self) -> None:
        class_name = "DeltaScreenBotNativeWindow"
        wnd_class = WNDCLASSW()
        wnd_class.lpfnWndProc = self.proc
        wnd_class.hInstance = self.instance
        wnd_class.lpszClassName = class_name
        wnd_class.hCursor = user32.LoadCursorW(None, 32512)
        wnd_class.hbrBackground = ctypes.cast(6, wintypes.HBRUSH)
        user32.RegisterClassW(ctypes.byref(wnd_class))
        self.hwnd = user32.CreateWindowExW(
            0, class_name, "DeltaScreenBot 测试版", WS_OVERLAPPEDWINDOW | WS_VISIBLE,
            CW_USEDEFAULT, CW_USEDEFAULT, 700, 330, None, None, self.instance, None
        )
        self.add_controls()

    def add_controls(self) -> None:
        static_style = WS_CHILD | WS_VISIBLE
        button_style = WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON
        user32.CreateWindowExW(0, "STATIC", "当前版本：屏幕识别流程 dry-run 测试", static_style,
                               30, 25, 600, 30, self.hwnd, None, self.instance, None)
        user32.CreateWindowExW(0, "STATIC", "开始机密流程：", static_style,
                               30, 80, 160, 30, self.hwnd, None, self.instance, None)
        user32.CreateWindowExW(0, "BUTTON", "机密（190000）", button_style,
                               210, 74, 180, 42, self.hwnd, BUTTON_CONFIDENTIAL, self.instance, None)
        user32.CreateWindowExW(0, "STATIC", "开始绝密流程：", static_style,
                               30, 140, 160, 30, self.hwnd, None, self.instance, None)
        user32.CreateWindowExW(0, "BUTTON", "绝密（600000）", button_style,
                               210, 134, 180, 42, self.hwnd, BUTTON_CLASSIFIED, self.instance, None)
        user32.CreateWindowExW(0, "BUTTON", "停止", button_style,
                               420, 104, 150, 42, self.hwnd, BUTTON_STOP, self.instance, None)
        self.status = user32.CreateWindowExW(0, "STATIC", "状态：就绪", static_style,
                                             30, 215, 600, 50, self.hwnd, STATUS_ID, self.instance, None)

    def set_status(self, text: str) -> None:
        if self.status:
            user32.SetWindowTextW(self.status, text)

    def start(self, mode: str, value: int) -> None:
        try:
            config = load_config(bundled_path("config/loadouts.yaml"))
            plan = Workflow(config, InputController(dry_run=True)).plan_from_detected_mode(mode, value)
            backpack = plan["loadout"].get("backpack", "未配置")
            self.set_status(f"状态：已生成 {mode} 方案；背包：{backpack}；当前为 dry-run")
        except Exception as exc:
            self.set_status(f"状态：错误：{exc}")

    def window_proc(self, hwnd, message, wparam, lparam):
        if message == WM_COMMAND:
            control_id = wparam & 0xFFFF
            if control_id == BUTTON_CONFIDENTIAL:
                self.start("机密", 190000)
            elif control_id == BUTTON_CLASSIFIED:
                self.start("绝密", 600000)
            elif control_id == BUTTON_STOP:
                self.set_status("状态：已停止")
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
