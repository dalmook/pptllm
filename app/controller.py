"""GUI와 실행 엔진을 연결하는 오케스트레이터."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.binders.anchor_fill_binder import AnchorFillBinder
from app.binders.chart_binder import ChartBinder
from app.binders.repeat_row_binder import RepeatRowBinder
from app.binders.table_binder import TableBinder
from app.binders.text_binder import TextBinder
from app.config_loader import ConfigLoader
from app.db import OracleExecutor
from app.models import AppPaths, ExecutionSummary, ReportMap, ShapeBindingConfig
from app.ppt_session import PowerPointSession
from app.sql_loader import SqlLoader
from app.utils.file_helpers import ensure_dir, ensure_file


class AppController:
    """실행 엔진 v1 컨트롤러."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.config_loader = ConfigLoader()
        self.sql_loader = SqlLoader(logger=logger)
        self.text_binder = TextBinder(logger=logger)
        self.table_binder = TableBinder(logger=logger)
        self.repeat_row_binder = RepeatRowBinder(logger=logger)
        self.anchor_fill_binder = AnchorFillBinder(logger=logger)
        self.chart_binder = ChartBinder(logger=logger)

    def run(self, paths: AppPaths) -> ExecutionSummary:
        """실행 엔진 v1 전체 흐름을 수행한다."""

        self.logger.info("실행 엔진 v1 시작")
        self._validate_input_paths(paths)

        report_map = self.config_loader.load(paths.config_file)
        self.logger.info("리포트 설정 로드 완료: %s", report_map.report_name)

        sql_map = self.sql_loader.scan(paths.sql_dir)

        sql_keys = self._collect_sql_keys(report_map.bindings)
        self._validate_sql_keys(sql_keys, sql_map)

        query_results = self._execute_queries(report_map.bindings, sql_map, report_map)

        output_file = paths.output_dir / self._build_output_name(report_map.output_filename_prefix)
        binding_results = self._run_binders(report_map.bindings, paths.ppt_template, output_file, query_results)

        self.logger.info("실행 엔진 v1 완료")
        return ExecutionSummary(
            report_name=report_map.report_name,
            output_file=output_file,
            sql_count=len(query_results),
            binding_results=binding_results,
        )

    def _validate_input_paths(self, paths: AppPaths) -> None:
        ensure_file(paths.ppt_template, "PowerPoint 템플릿")
        ensure_file(paths.config_file, "설정")
        ensure_dir(paths.sql_dir, "SQL")
        ensure_dir(paths.output_dir, "출력")

    def _collect_sql_keys(self, bindings: list[ShapeBindingConfig]) -> set[str]:
        keys: set[str] = set()
        for b in bindings:
            if b.enabled and b.sql_key:
                keys.add(b.sql_key)
        return keys

    def _validate_sql_keys(self, required_keys: set[str], sql_map: dict[str, str]) -> None:
        missing = sorted([key for key in required_keys if key not in sql_map])
        if missing:
            raise ValueError(f"설정에서 참조한 SQL_KEY를 sql 폴더에서 찾지 못했습니다: {', '.join(missing)}")

    def _execute_queries(
        self,
        bindings: list[ShapeBindingConfig],
        sql_map: dict[str, str],
        report_map: ReportMap,
    ) -> dict[str, list[dict[str, Any]]]:
        query_results: dict[str, list[dict[str, Any]]] = {}

        required_sql_keys = self._collect_sql_keys(bindings)
        if not required_sql_keys:
            self.logger.info("실행할 SQL_KEY가 없습니다. DB 조회를 건너뜁니다.")
            return query_results

        with OracleExecutor(report_map.db, logger=self.logger) as oracle:
            for sql_key in sorted(required_sql_keys):
                self.logger.info("SQL 실행: %s", sql_key)
                query_results[sql_key] = oracle.query(sql_map[sql_key])
        return query_results

    def _run_binders(
        self,
        bindings: list[ShapeBindingConfig],
        template_path: Path,
        output_path: Path,
        query_results: dict[str, list[dict[str, Any]]],
    ) -> dict[str, str]:
        results: dict[str, str] = {}
        with PowerPointSession(template_path, output_path, logger=self.logger) as ppt:
            for binding in bindings:
                if not binding.enabled:
                    self.logger.debug("비활성 바인딩 스킵: %s", binding.shape_name)
                    continue

                self.logger.info("바인딩 처리: shape=%s type=%s", binding.shape_name, binding.bind_type)
                if binding.bind_type == "text":
                    results[binding.shape_name] = self.text_binder.bind(ppt, binding, query_results)
                elif binding.bind_type == "tbl":
                    results[binding.shape_name] = self.table_binder.bind(ppt, binding, query_results)
                elif binding.bind_type == "tblr":
                    results[binding.shape_name] = self.repeat_row_binder.bind(ppt, binding, query_results)
                elif binding.bind_type == "tblx":
                    results[binding.shape_name] = self.anchor_fill_binder.bind(ppt, binding, query_results)
                elif binding.bind_type == "cht":
                    results[binding.shape_name] = self.chart_binder.bind(ppt, binding, query_results)
                else:
                    self.logger.warning("지원하지 않는 bind_type입니다: %s", binding.bind_type)

            ppt.save_as_output()

        return results

    @staticmethod
    def _build_output_name(prefix: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{stamp}.pptx"

    @staticmethod
    def normalize_paths(ppt_path: str, config_path: str, sql_dir: str, output_dir: str) -> AppPaths:
        return AppPaths(
            ppt_template=Path(ppt_path).expanduser(),
            config_file=Path(config_path).expanduser(),
            sql_dir=Path(sql_dir).expanduser(),
            output_dir=Path(output_dir).expanduser(),
        )
