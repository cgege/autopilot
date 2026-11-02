from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from .config import load_config
from .input_control import InputController
from .workflow import Workflow


def bundled_path(relative: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / relative


class BotApp(tk.Tk):
    """Small desktop shell for the automation worker."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Delta PC Screen Automation")
        self.geometry("560x360")
        self.resizable(False, False)
        self.stop_event = threading.Event()
        self.messages: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None

        form = ttk.Frame(self, padding=16)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="模式").grid(row=0, column=0, sticky="w")
        self.mode_var = tk.StringVar(value="机密")
        ttk.Combobox(form, textvariable=self.mode_var, values=("机密", "绝密"),
                     state="readonly", width=27).grid(row=0, column=1, sticky="ew")
        ttk.Label(form, text="当前装备价值").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.threshold_var = tk.StringVar(value="190000")
        ttk.Entry(form, textvariable=self.threshold_var, width=30).grid(row=1, column=1, sticky="ew", pady=(8, 0))

        buttons = ttk.Frame(form)
        buttons.grid(row=2, column=0, columnspan=2, sticky="w", pady=14)
        self.toggle_button = ttk.Button(buttons, text="开始", command=self.toggle_run)
        self.toggle_button.pack(side="left")
        self.status_var = tk.StringVar(value="就绪（默认 dry-run）")
        ttk.Label(form, textvariable=self.status_var).grid(row=3, column=0, columnspan=2, sticky="w")
        self.log = tk.Text(form, height=12, width=64, state="disabled")
        self.log.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        form.columnconfigure(1, weight=1)
        self.after(100, self.flush_messages)

    def write(self, message: str) -> None:
        self.messages.put(message)

    def toggle_run(self) -> None:
        if self.worker and self.worker.is_alive():
            self.stop()
        else:
            self.start()

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        self.stop_event.clear()
        self.toggle_button.configure(text="停止", state="normal")
        self.status_var.set("运行中")
        self.worker = threading.Thread(target=self.run_worker, daemon=True)
        self.worker.start()

    def stop(self) -> None:
        if not self.worker or not self.worker.is_alive():
            return
        self.stop_event.set()
        self.toggle_button.configure(text="停止中", state="disabled")
        self.status_var.set("正在停止")
        self.write("收到停止请求；后续动作将在当前步骤结束后停止。")

    def run_worker(self) -> None:
        try:
            config = load_config(bundled_path("config/loadouts.yaml"))
            threshold = int(self.threshold_var.get())
            plan = Workflow(config, InputController(dry_run=True)).plan_from_detected_mode(
                self.mode_var.get(), threshold
            )
            if self.stop_event.is_set():
                return
            self.write(f"已生成执行方案：{plan['loadout_name']}")
            self.write("当前版本执行识别与方案预览，实际点击将在模板采集完成后启用。")
        except Exception as exc:  # keep GUI alive and show actionable error
            self.write(f"错误：{exc}")
        finally:
            self.after(0, self.worker_finished)

    def worker_finished(self) -> None:
        self.toggle_button.configure(text="开始", state="normal")
        if self.status_var.get() != "正在停止":
            self.status_var.set("已完成")
        else:
            self.status_var.set("已停止")

    def flush_messages(self) -> None:
        while not self.messages.empty():
            message = self.messages.get_nowait()
            self.log.configure(state="normal")
            self.log.insert("end", message + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.after(100, self.flush_messages)


def main() -> None:
    BotApp().mainloop()


if __name__ == "__main__":
    main()
