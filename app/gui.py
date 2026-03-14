"""Tkinter 기반 데스크톱 GUI."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from app.controller import AppController


class TkTextHandler(logging.Handler):
    """logging 레코드를 Tk Text 위젯에 출력하는 핸들러."""

    def __init__(self, text_widget: tk.Text) -> None:
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        self.text_widget.after(0, self._append, message)

    def _append(self, message: str) -> None:
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, message + "\n")
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")


class ReportAutomationApp(tk.Tk):
    """보고서 자동화 도구 메인 윈도우."""

    def __init__(self, controller: AppController, logger: logging.Logger) -> None:
        super().__init__()
        self.controller = controller
        self.logger = logger

        self.title("PPT 보고서 자동화 도구 (Engine v1)")
        self.geometry("920x680")

        self.ppt_var = tk.StringVar()
        self.config_var = tk.StringVar(value="config/report_map.json")
        self.sql_dir_var = tk.StringVar(value="sql")
        self.output_dir_var = tk.StringVar(value="output")
        self.status_var = tk.StringVar(value="대기 중")

        self._build_ui()
        self._connect_logging()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        self._make_path_row(frame, 0, "PowerPoint 템플릿", self.ppt_var, self._select_ppt_file)
        self._make_path_row(frame, 1, "설정 JSON 파일", self.config_var, self._select_config_file)
        self._make_path_row(frame, 2, "SQL 폴더", self.sql_dir_var, self._select_sql_dir)
        self._make_path_row(frame, 3, "Output 폴더", self.output_dir_var, self._select_output_dir)

        run_button = ttk.Button(frame, text="실행", command=self._on_run_clicked)
        run_button.grid(row=4, column=0, pady=(12, 8), sticky="w")

        ttk.Label(frame, text="실행 로그").grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 4))

        self.log_text = tk.Text(frame, height=24, state="disabled")
        self.log_text.grid(row=6, column=0, columnspan=3, sticky="nsew")

        status_bar = ttk.Label(frame, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(6, weight=1)

    def _connect_logging(self) -> None:
        handler = TkTextHandler(self.log_text)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(handler)

    def _make_path_row(
        self,
        parent: ttk.Frame,
        row: int,
        title: str,
        variable: tk.StringVar,
        browse_command: Callable[[], None],
    ) -> None:
        ttk.Label(parent, text=title).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Button(parent, text="찾아보기", command=browse_command).grid(row=row, column=2, pady=4)

    def _select_ppt_file(self) -> None:
        path = filedialog.askopenfilename(
            title="PowerPoint 템플릿 선택",
            filetypes=[("PowerPoint", "*.pptx *.pptm"), ("All Files", "*.*")],
        )
        if path:
            self.ppt_var.set(path)

    def _select_config_file(self) -> None:
        path = filedialog.askopenfilename(
            title="설정 파일 선택",
            filetypes=[("JSON", "*.json"), ("All Files", "*.*")],
        )
        if path:
            self.config_var.set(path)

    def _select_sql_dir(self) -> None:
        path = filedialog.askdirectory(title="SQL 폴더 선택")
        if path:
            self.sql_dir_var.set(path)

    def _select_output_dir(self) -> None:
        path = filedialog.askdirectory(title="출력 폴더 선택")
        if path:
            self.output_dir_var.set(path)

    def _on_run_clicked(self) -> None:
        try:
            self.status_var.set("실행 중...")
            self.logger.info("사용자 실행 요청 수신")
            paths = self.controller.normalize_paths(
                self.ppt_var.get(),
                self.config_var.get(),
                self.sql_dir_var.get(),
                self.output_dir_var.get(),
            )
            summary = self.controller.run(paths)
            self.status_var.set("완료")
            messagebox.showinfo(
                "완료",
                "실행이 완료되었습니다.\n"
                f"리포트: {summary.report_name}\n"
                f"실행 SQL 수: {summary.sql_count}\n"
                f"결과 파일: {summary.output_file}",
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.status_var.set("오류")
            self.logger.exception("실행 중 오류 발생")
            messagebox.showerror("오류", f"실행에 실패했습니다.\n원인: {exc}")
