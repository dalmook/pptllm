"""LLM 프롬프트/입력 payload 빌더."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.models import PptShapeAnalysis, PptStructureReport


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


def build_map_generation_payload(
    structure: PptStructureReport,
    sql_keys: list[str],
    user_hints: str | None = None,
) -> dict[str, Any]:
    """LLM 전달용 간결 payload를 만든다."""

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
        "output_schema": {
            "bindings": [
                {
                    "shape_name": "string",
                    "slide_index": "int",
                    "recommended_bind_type": "text|tbl|tblr|tblx|cht|none",
                    "sql_key_candidate": "string|null",
                    "header_row": "int|null",
                    "template_row": "int|null",
                    "key_fields": ["string"],
                    "columns": ["string"],
                    "category_field": "string|null",
                    "series_fields": ["string"],
                    "enabled": "bool",
                    "confidence": "0.0~1.0",
                    "reason": "string",
                    "notes": ["string"],
                }
            ]
        },
    }


def build_map_generation_prompt(payload: dict[str, Any]) -> str:
    """OpenAI-compatible 모델에 전달할 system/user 지시 문자열을 생성한다."""

    return (
        "당신은 PowerPoint 자동화 설정 초안을 만드는 도우미입니다. "
        "반드시 JSON만 출력하세요. markdown 금지. \n"
        "규칙: bind_type은 text/tbl/tblr/tblx/cht/none 중 하나, confidence는 0~1. "
        "완벽한 정답이 아니라 '초안'임을 notes에 포함하세요. \n"
        f"입력 payload: {asdict_like(payload)}"
    )


def asdict_like(data: Any) -> str:
    """외부 의존성 없이 prompt에 넣기 위한 문자열화."""

    return str(data)
