"""GUI와 실행 엔진을 연결하는 오케스트레이터."""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from app.binders.anchor_fill_binder import AnchorFillBinder
from app.binders.chart_binder import ChartBinder
from app.binders.repeat_row_binder import RepeatRowBinder
from app.binders.table_binder import TableBinder
from app.binders.text_binder import TextBinder
from app.config_loader import ConfigLoader
from app.db import OracleExecutor
from app.debug_reporter import DebugReporter
from app.llm_helper import LLMHelper
from app.map_generator import MapGenerator
from app.models import (
    AppPaths,
    PptShapeAnalysis,
    PptStructureReport,
    ReportMap,
    ReportMapDraft,
    RunExecutionSummary,
    ShapeBindingConfig,
    ShapeExecutionResult,
)
from app.ppt_analyzer import PptAnalyzer
from app.ppt_session import PowerPointSession
from app.sql_loader import SqlLoader
from app.utils.file_helpers import ensure_dir, ensure_file
from app.utils.formatters import format_korean_now


class AppController:
    """실행 엔진 v5 컨트롤러."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.config_loader = ConfigLoader()
        self.sql_loader = SqlLoader(logger=logger)
        self.text_binder = TextBinder(logger=logger)
        self.table_binder = TableBinder(logger=logger)
        self.repeat_row_binder = RepeatRowBinder(logger=logger)
        self.anchor_fill_binder = AnchorFillBinder(logger=logger)
        self.chart_binder = ChartBinder(logger=logger)
        self.debug_reporter = DebugReporter()
        self.ppt_analyzer = PptAnalyzer(logger=logger)
        self.map_generator = MapGenerator()

    def run(self, paths: AppPaths) -> RunExecutionSummary:
        """실행 엔진 전체 흐름을 수행하고 디버그 리포트를 생성한다."""

        started = perf_counter()
        executed_at = format_korean_now()
        self.logger.info("실행 엔진 v5 시작")

        summary = RunExecutionSummary(
            executed_at=executed_at,
            template_file=str(paths.ppt_template),
            output_file="",
            config_file=str(paths.config_file),
            sql_dir=str(paths.sql_dir),
            loaded_sql_keys=[],
            sql_row_counts={},
            total_elapsed_ms=0,
        )

        try:
            self._validate_input_paths(paths)
            report_map = self.config_loader.load(paths.config_file)
            self.logger.info("리포트 설정 로드 완료: %s", report_map.report_name)

            sql_map = self.sql_loader.scan(paths.sql_dir)
            summary.loaded_sql_keys = sorted(sql_map.keys())

            sql_keys = self._collect_sql_keys(report_map.bindings)
            self._validate_sql_keys(sql_keys, sql_map)

            query_results = self._execute_queries(report_map.bindings, sql_map, report_map)
            summary.sql_row_counts = {k: len(v) for k, v in query_results.items()}

            output_file = paths.output_dir / self._build_output_name(report_map.output_filename_prefix)
            summary.output_file = str(output_file)

            summary.shape_results = self._run_binders(report_map.bindings, paths.ppt_template, output_file, query_results)
            self._finalize_counts(summary)
        except Exception as exc:  # pylint: disable=broad-except
            summary.exception_message = str(exc)
            summary.stack_trace = traceback.format_exc()
            self.logger.exception("실행 엔진 실패")
            raise
        finally:
            summary.total_elapsed_ms = int((perf_counter() - started) * 1000)
            self.debug_reporter.write(paths.output_dir, summary)
            self.logger.info(
                "실행 엔진 v5 종료 - 성공:%d 경고:%d 실패:%d 건너뜀:%d",
                summary.success_count,
                summary.warning_count,
                summary.failure_count,
                summary.skipped_count,
            )

        return summary

    def analyze_ppt_structure(self, template_path: Path, output_dir: Path) -> tuple[PptStructureReport, Path, Path]:
        ensure_file(template_path, "PowerPoint 템플릿")
        ensure_dir(output_dir, "출력")
        self.logger.info("PPT 구조 분석 시작: %s", template_path)
        report, json_path, md_path = self.ppt_analyzer.analyze(template_path, output_dir)
        self.logger.info("PPT 구조 분석 완료: json=%s md=%s", json_path, md_path)
        return report, json_path, md_path

    def generate_map_draft_with_llm(
        self,
        template_path: Path,
        output_dir: Path,
        sql_dir: Path,
        user_hints: str | None = None,
    ) -> tuple[ReportMapDraft, Path, Path]:
        """PPT 구조 분석 결과를 기반으로 report_map.generated 초안을 만든다."""

        ensure_file(template_path, "PowerPoint 템플릿")
        ensure_dir(output_dir, "출력")
        ensure_dir(sql_dir, "SQL")

        structure_json = output_dir / "ppt_structure.json"
        if structure_json.exists():
            self.logger.info("기존 구조 분석 결과를 사용합니다: %s", structure_json)
            structure = self._load_structure_report(structure_json)
        else:
            self.logger.info("구조 분석 결과가 없어 먼저 분석을 실행합니다.")
            structure, _, _ = self.analyze_ppt_structure(template_path, output_dir)

        sql_map = self.sql_loader.scan(sql_dir)
        sql_keys = sorted(sql_map.keys())

        helper = LLMHelper.from_env()
        self.logger.info("LLM map 초안 생성 시작: provider=%s model=%s", helper.provider.name, helper.provider.model)
        draft = helper.generate_report_map_draft(structure=structure, sql_keys=sql_keys, user_hints=user_hints)

        json_path, md_path = self.map_generator.write(output_dir, draft)
        self.logger.info("LLM map 초안 생성 완료: json=%s md=%s", json_path, md_path)
        return draft, json_path, md_path

    def _validate_input_paths(self, paths: AppPaths) -> None:
        ensure_file(paths.ppt_template, "PowerPoint 템플릿")
        ensure_file(paths.config_file, "설정")
        ensure_dir(paths.sql_dir, "SQL")
        ensure_dir(paths.output_dir, "출력")

    def _collect_sql_keys(self, bindings: list[ShapeBindingConfig]) -> set[str]:
        return {b.sql_key for b in bindings if b.enabled and b.sql_key}

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
                self.logger.debug("SQL 실행 결과: key=%s rows=%d", sql_key, len(query_results[sql_key]))
        return query_results

    def _run_binders(
        self,
        bindings: list[ShapeBindingConfig],
        template_path: Path,
        output_path: Path,
        query_results: dict[str, list[dict[str, Any]]],
    ) -> list[ShapeExecutionResult]:
        results: list[ShapeExecutionResult] = []

        with PowerPointSession(template_path, output_path, logger=self.logger) as ppt:
            for binding in bindings:
                started = perf_counter()
                started_at = format_korean_now()
                row_count = len(query_results.get(binding.sql_key or "", []))
                meta = self._build_meta(binding)

                if not binding.enabled:
                    results.append(
                        ShapeExecutionResult(
                            shape_name=binding.shape_name,
                            shape_type="unknown",
                            bind_type=binding.bind_type,
                            sql_key=binding.sql_key,
                            enabled=False,
                            status="skipped",
                            message="비활성 설정으로 건너뜀",
                            row_count=row_count,
                            started_at=started_at,
                            ended_at=format_korean_now(),
                            elapsed_ms=0,
                            meta=meta,
                        )
                    )
                    continue

                self.logger.info(
                    "바인딩 처리 시작: shape=%s type=%s sql_key=%s row_count=%d",
                    binding.shape_name,
                    binding.bind_type,
                    binding.sql_key,
                    row_count,
                )

                try:
                    message = self._dispatch_binder(ppt, binding, query_results)
                    status = self._status_from_message(message)
                    slide, shape = ppt.find_shape(binding.shape_name)
                    shape_type = ppt.detect_shape_type(shape)
                    elapsed_ms = int((perf_counter() - started) * 1000)
                    meta = self._apply_message_meta(meta, binding.bind_type, message, row_count)
                    result = ShapeExecutionResult(
                        shape_name=binding.shape_name,
                        shape_type=shape_type,
                        bind_type=binding.bind_type,
                        sql_key=binding.sql_key,
                        enabled=True,
                        status=status,
                        message=message,
                        row_count=row_count,
                        started_at=started_at,
                        ended_at=format_korean_now(),
                        elapsed_ms=elapsed_ms,
                        meta={**meta, "slide_index": slide},
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    elapsed_ms = int((perf_counter() - started) * 1000)
                    result = ShapeExecutionResult(
                        shape_name=binding.shape_name,
                        shape_type="unknown",
                        bind_type=binding.bind_type,
                        sql_key=binding.sql_key,
                        enabled=True,
                        status="failed",
                        message=str(exc),
                        row_count=row_count,
                        started_at=started_at,
                        ended_at=format_korean_now(),
                        elapsed_ms=elapsed_ms,
                        meta=meta,
                    )
                    self.logger.exception("shape 처리 실패: %s", binding.shape_name)

                results.append(result)
                self.logger.info("바인딩 결과: %s -> %s", binding.shape_name, result.status)

            ppt.save_as_output()

        return results

    def _dispatch_binder(
        self,
        ppt: PowerPointSession,
        binding: ShapeBindingConfig,
        query_results: dict[str, list[dict[str, Any]]],
    ) -> str:
        if binding.bind_type == "text":
            return self.text_binder.bind(ppt, binding, query_results)
        if binding.bind_type == "tbl":
            return self.table_binder.bind(ppt, binding, query_results)
        if binding.bind_type == "tblr":
            return self.repeat_row_binder.bind(ppt, binding, query_results)
        if binding.bind_type == "tblx":
            return self.anchor_fill_binder.bind(ppt, binding, query_results)
        if binding.bind_type == "cht":
            return self.chart_binder.bind(ppt, binding, query_results)
        raise ValueError(f"지원하지 않는 bind_type입니다: {binding.bind_type}")

    @staticmethod
    def _status_from_message(message: str) -> str:
        if message.startswith("OK:"):
            return "success"
        if message.startswith("WARN:"):
            return "warning"
        return "success"

    @staticmethod
    def _build_meta(binding: ShapeBindingConfig) -> dict[str, Any]:
        if binding.bind_type == "tbl":
            return {"columns": binding.columns, "header_row": binding.header_row}
        if binding.bind_type == "tblr":
            return {
                "template_row": binding.template_row,
                "generated_rows": 0,
                "keep_template_row_if_empty": binding.keep_template_row_if_empty,
                "clear_placeholders_if_empty": binding.clear_placeholders_if_empty,
            }
        if binding.bind_type == "tblx":
            return {
                "header_row": binding.header_row,
                "key_fields": binding.key_fields,
                "anchor_count": 0,
                "matched_count": 0,
                "unmatched_count": 0,
            }
        if binding.bind_type == "cht":
            return {
                "category_field": binding.category_field,
                "series_fields": binding.series_fields,
            }
        return {}

    @staticmethod
    def _apply_message_meta(meta: dict[str, Any], bind_type: str, message: str, row_count: int) -> dict[str, Any]:
        updated = dict(meta)
        if bind_type == "tblr":
            updated["generated_rows"] = row_count
        if bind_type == "tblx":
            for token, key in (("anchor=", "anchor_count"), ("match=", "matched_count"), ("empty=", "unmatched_count")):
                if token in message:
                    try:
                        updated[key] = int(message.split(token, 1)[1].split()[0])
                    except Exception:  # pylint: disable=broad-except
                        pass
        return updated

    @staticmethod
    def _build_output_name(prefix: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{stamp}.pptx"

    @staticmethod
    def _finalize_counts(summary: RunExecutionSummary) -> None:
        summary.success_count = sum(1 for r in summary.shape_results if r.status == "success")
        summary.warning_count = sum(1 for r in summary.shape_results if r.status == "warning")
        summary.failure_count = sum(1 for r in summary.shape_results if r.status == "failed")
        summary.skipped_count = sum(1 for r in summary.shape_results if r.status == "skipped")

    @staticmethod
    def _load_structure_report(path: Path) -> PptStructureReport:
        payload = json.loads(path.read_text(encoding="utf-8"))
        by_slide: dict[int, list[PptShapeAnalysis]] = {}
        for slide_key, items in payload.get("by_slide", {}).items():
            slide_index = int(slide_key)
            by_slide[slide_index] = [PptShapeAnalysis(**item) for item in items]
        return PptStructureReport(
            analyzed_at=payload.get("analyzed_at", ""),
            template_file=payload.get("template_file", ""),
            output_dir=payload.get("output_dir", ""),
            total_shapes=int(payload.get("total_shapes", 0)),
            by_slide=by_slide,
        )

    @staticmethod
    def normalize_paths(ppt_path: str, config_path: str, sql_dir: str, output_dir: str) -> AppPaths:
        return AppPaths(
            ppt_template=Path(ppt_path).expanduser(),
            config_file=Path(config_path).expanduser(),
            sql_dir=Path(sql_dir).expanduser(),
            output_dir=Path(output_dir).expanduser(),
        )
