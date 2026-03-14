"""Tkinter 기반 데스크톱 GUI."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
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

        self.title("PPT 보고서 자동화 도구 (Engine v5)")
        self.geometry("1030x760")

        self.ppt_var = tk.StringVar()
        self.config_var = tk.StringVar(value="config/report_map.json")
        self.sql_dir_var = tk.StringVar(value="sql")
        self.output_dir_var = tk.StringVar(value="output")
        self.status_var = tk.StringVar(value="대기 중")
        self.last_files_var = tk.StringVar(value="최근 생성 파일: 없음")

        self._build_ui()
        self._connect_logging()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        self._make_path_row(frame, 0, "PowerPoint 템플릿", self.ppt_var, self._select_ppt_file)
        self._make_path_row(frame, 1, "설정 JSON 파일", self.config_var, self._select_config_file)
        self._make_path_row(frame, 2, "SQL 폴더", self.sql_dir_var, self._select_sql_dir)
        self._make_path_row(frame, 3, "Output 폴더", self.output_dir_var, self._select_output_dir)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 8))

        ttk.Button(btn_frame, text="실행", command=self._on_run_clicked).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="PPT 구조 분석", command=self._on_analyze_clicked).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="LLM으로 map 초안 생성", command=self._on_generate_map_clicked).pack(side="left")

        ttk.Label(frame, textvariable=self.last_files_var).grid(row=5, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="실행 로그").grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 4))

        self.log_text = tk.Text(frame, height=26, state="disabled")
        self.log_text.grid(row=7, column=0, columnspan=3, sticky="nsew")

        status_bar = ttk.Label(frame, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(7, weight=1)

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

            debug_json = Path(paths.output_dir) / "debug_report.json"
            debug_md = Path(paths.output_dir) / "debug_report.md"
            self.last_files_var.set(f"최근 생성 파일: {summary.output_file}, {debug_json}, {debug_md}")

            messagebox.showinfo(
                "완료",
                "실행이 완료되었습니다.\n"
                f"성공/경고/실패/건너뜀: {summary.success_count}/{summary.warning_count}/"
                f"{summary.failure_count}/{summary.skipped_count}\n"
                f"결과 파일: {summary.output_file}\n"
                f"디버그 리포트: {debug_json}\n{debug_md}",
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.status_var.set("오류")
            self.logger.exception("실행 중 오류 발생")
            messagebox.showerror("오류", f"실행에 실패했습니다.\n원인: {exc}")

    def _on_analyze_clicked(self) -> None:
        try:
            self.status_var.set("구조 분석 중...")
            template = Path(self.ppt_var.get()).expanduser()
            output_dir = Path(self.output_dir_var.get()).expanduser()
            report, json_path, md_path = self.controller.analyze_ppt_structure(template, output_dir)
            self.status_var.set("구조 분석 완료")
            self.last_files_var.set(f"최근 생성 파일: {json_path}, {md_path}")
            messagebox.showinfo(
                "구조 분석 완료",
                f"총 shape 수: {report.total_shapes}\nJSON: {json_path}\nMD: {md_path}",
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.status_var.set("오류")
            self.logger.exception("구조 분석 중 오류 발생")
            messagebox.showerror("오류", f"구조 분석에 실패했습니다.\n원인: {exc}")

    def _on_generate_map_clicked(self) -> None:
        try:
            self.status_var.set("LLM 초안 생성 중...")
            template = Path(self.ppt_var.get()).expanduser()
            output_dir = Path(self.output_dir_var.get()).expanduser()
            sql_dir = Path(self.sql_dir_var.get()).expanduser()

            hints = simpledialog.askstring(
                "선택 힌트",
                "선택적으로 힌트를 입력하세요 (예: 특정 shape는 tblx로 우선 고려):",
                parent=self,
            )

            draft, json_path, md_path = self.controller.generate_map_draft_with_llm(
                template_path=template,
                output_dir=output_dir,
                sql_dir=sql_dir,
                user_hints=hints,
            )
            self.status_var.set("LLM 초안 생성 완료")
            self.last_files_var.set(f"최근 생성 파일: {json_path}, {md_path}")
            messagebox.showinfo(
                "LLM 초안 생성 완료",
                f"Provider/Model: {draft.llm_provider}/{draft.llm_model}\n"
                f"바인딩 초안 개수: {len(draft.bindings)}\n"
                f"JSON: {json_path}\nMD: {md_path}\n\n"
                "※ generated 파일은 초안입니다. 반드시 사람이 검토 후 반영하세요.",
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.status_var.set("오류")
            self.logger.exception("LLM 초안 생성 중 오류 발생")
            messagebox.showerror("오류", f"LLM 초안 생성에 실패했습니다.\n원인: {exc}")
