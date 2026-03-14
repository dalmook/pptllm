"""애플리케이션 데이터 모델 정의."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

BindType = Literal["text", "tbl", "tblr", "tblx", "cht"]


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


@dataclass(slots=True)
class ReportMap:
    """report_map.json 전체 구조."""

    report_name: str
    db: dict[str, str] = field(default_factory=dict)
    output_filename_prefix: str = "report"
    bindings: list[ShapeBindingConfig] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionSummary:
    """실행 요약 결과."""

    report_name: str
    output_file: Path
    sql_count: int
    binding_results: dict[str, str] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
