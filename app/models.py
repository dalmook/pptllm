"""애플리케이션 데이터 모델 정의."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

BindType = Literal["text", "tbl", "tblr", "tblx", "cht"]
ShapeType = Literal["text", "table", "chart", "unknown"]
RunStatus = Literal["success", "warning", "failed", "skipped"]


@dataclass(slots=True)
class AppPaths:
    """GUI에서 전달받은 경로 집합."""

    ppt_template: Path
    config_file: Path
    sql_dir: Path
    output_dir: Path


@dataclass(slots=True)
class ShapeBindingConfig:
    """shape 단위 바인딩 설정."""

    shape_name: str
    bind_type: BindType
    sql_key: str | None = None
    columns: list[str] = field(default_factory=list)
    header_row: int = 1
    template_row: int = 2
    key_fields: list[str] = field(default_factory=list)
    category_field: str | None = None
    series_fields: list[str] = field(default_factory=list)
    clear_existing: bool = True
    enabled: bool = True
    strict_match: bool = False
    keep_template_row_if_empty: bool = True
    clear_placeholders_if_empty: bool = True


@dataclass(slots=True)
class ReportMap:
    """report_map.json 전체 구조."""

    report_name: str
    db: dict[str, str] = field(default_factory=dict)
    output_filename_prefix: str = "report"
    bindings: list[ShapeBindingConfig] = field(default_factory=list)


@dataclass(slots=True)
class ShapeExecutionResult:
    """shape 단위 실행 결과."""

    shape_name: str
    shape_type: ShapeType
    bind_type: str
    sql_key: str | None
    enabled: bool
    status: RunStatus
    message: str
    row_count: int
    started_at: str
    ended_at: str
    elapsed_ms: int
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RunExecutionSummary:
    """전체 실행 결과 요약."""

    executed_at: str
    template_file: str
    output_file: str
    config_file: str
    sql_dir: str
    loaded_sql_keys: list[str]
    sql_row_counts: dict[str, int]
    total_elapsed_ms: int
    shape_results: list[ShapeExecutionResult] = field(default_factory=list)
    success_count: int = 0
    warning_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    exception_message: str | None = None
    stack_trace: str | None = None


@dataclass(slots=True)
class PptShapeAnalysis:
    """PPT shape 구조 분석 결과."""

    shape_name: str
    slide_index: int
    shape_type: ShapeType
    has_text: bool
    text_preview: str
    has_table: bool
    table_rows: int
    table_cols: int
    header_row_candidates: list[int] = field(default_factory=list)
    table_preview: list[list[str]] = field(default_factory=list)
    has_chart: bool = False
    chart_series_names: list[str] = field(default_factory=list)
    placeholder_candidates: list[str] = field(default_factory=list)
    anchor_token_candidates: list[str] = field(default_factory=list)
    recommended_bind_type: str = "none"
    recommendation_reason: str = ""
    recommended_header_row: int | None = None
    recommended_template_row: int | None = None
    recommended_key_fields_hints: list[str] = field(default_factory=list)
    anchor_cell_candidates: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PptStructureReport:
    """PPT 구조 분석 리포트."""

    analyzed_at: str
    template_file: str
    output_dir: str
    total_shapes: int
    by_slide: dict[int, list[PptShapeAnalysis]] = field(default_factory=dict)


@dataclass(slots=True)
class MapDraftBinding:
    """LLM이 생성한 report_map 초안의 shape 항목."""

    shape_name: str
    slide_index: int
    recommended_bind_type: str
    sql_key_candidate: str | None = None
    header_row: int | None = None
    template_row: int | None = None
    key_fields: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    category_field: str | None = None
    series_fields: list[str] = field(default_factory=list)
    enabled: bool = True
    confidence: float = 0.5
    reason: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ReportMapDraft:
    """LLM 생성 report_map 초안."""

    generated_at: str
    source_ppt: str
    llm_provider: str
    llm_model: str
    bindings: list[MapDraftBinding] = field(default_factory=list)
