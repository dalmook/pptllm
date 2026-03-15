"""LLM 프롬프트/입력 payload 빌더."""

from __future__ import annotations

from typing import Any

from app.models import MapDraftBinding, PptShapeAnalysis, PptStructureReport


def _compact_shape(shape: PptShapeAnalysis) -> dict[str, Any]:
    return {
        "shape_name": shape.shape_name,
        "slide_index": shape.slide_index,
        "shape_type": shape.shape_type,
        "text_preview": shape.text_preview,
        "has_table": shape.has_table,
        "table_rows": shape.table_rows,
        "table_cols": shape.table_cols,
        "header_row_candidates": shape.header_row_candidates,
        "table_preview": shape.table_preview[:2],
        "placeholder_candidates": shape.placeholder_candidates,
        "anchor_token_candidates": shape.anchor_token_candidates,
        "recommended_bind_type": shape.recommended_bind_type,
        "recommendation_reason": shape.recommendation_reason,
    }


def build_map_generation_payload(structure: PptStructureReport, sql_keys: list[str], user_hints: str | None = None) -> dict[str, Any]:
    shapes: list[dict[str, Any]] = []
    for slide_index in sorted(structure.by_slide.keys()):
        for shape in structure.by_slide[slide_index]:
            shapes.append(_compact_shape(shape))

    return {
        "task": "generate_report_map_draft",
        "source_ppt": structure.template_file,
        "sql_keys": sql_keys,
        "user_hints": user_hints or "",
        "shapes": shapes,
    }


def build_map_generation_prompt(payload: dict[str, Any]) -> str:
    return (
        "반드시 JSON만 출력하세요. report_map 초안을 생성하세요. "
        "bind_type은 text/tbl/tblr/tblx/cht/none 중 하나여야 하며 confidence는 0~1 범위여야 합니다. "
        "notes에는 반드시 사람이 검토해야 한다는 문구를 포함하세요. "
        f"입력 payload: {payload}"
    )


def build_sql_generation_payload(
    binding: MapDraftBinding,
    shape: PptShapeAnalysis | None,
    sql_keys: list[str],
    user_hint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "task": "generate_oracle_sql_draft",
        "shape_name": binding.shape_name,
        "slide_index": binding.slide_index,
        "bind_type": binding.recommended_bind_type,
        "sql_key_candidate": binding.sql_key_candidate,
        "header_row": binding.header_row,
        "template_row": binding.template_row,
        "key_fields": binding.key_fields,
        "columns": binding.columns,
        "category_field": binding.category_field,
        "series_fields": binding.series_fields,
        "shape_info": _compact_shape(shape) if shape else {},
        "available_sql_keys": sql_keys,
        "user_hint": user_hint or {},
    }


def build_sql_generation_prompt(payload: dict[str, Any]) -> str:
    return (
        "당신은 Oracle SQL 초안 생성기입니다. 반드시 JSON만 출력하세요. "
        "필수 필드: sql_key, confidence, assumptions, notes, expected_output_columns, review_points, sql_text. "
        "sql_text는 바로 파일 저장 가능한 Oracle SQL 이어야 하며 불필요한 컬럼을 최소화하세요. "
        "tblx는 key_fields + header alias 구조를 맞추고 CASE WHEN/집계 패턴을 고려하세요. "
        "이 결과는 초안이며 사람이 검토해야 함을 notes에 포함하세요. "
        f"입력 payload: {payload}"
    )
