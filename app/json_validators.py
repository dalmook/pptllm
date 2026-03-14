"""LLM 생성 JSON 정규화/검증 유틸."""

from __future__ import annotations

from typing import Any

from app.models import MapDraftBinding, ReportMapDraft
from app.utils.formatters import format_korean_now

_ALLOWED = {"text", "tbl", "tblr", "tblx", "cht", "none"}


def normalize_report_map_draft(
    raw: dict[str, Any],
    source_ppt: str,
    provider: str,
    model: str,
) -> ReportMapDraft:
    bindings_raw = raw.get("bindings", [])
    if not isinstance(bindings_raw, list):
        bindings_raw = []

    bindings: list[MapDraftBinding] = []
    for item in bindings_raw:
        if not isinstance(item, dict):
            continue
        bind_type = str(item.get("recommended_bind_type", "none")).lower()
        if bind_type not in _ALLOWED:
            bind_type = "none"

        confidence = _to_float(item.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        binding = MapDraftBinding(
            shape_name=str(item.get("shape_name", "")).strip(),
            slide_index=_to_int(item.get("slide_index", 0), 0),
            recommended_bind_type=bind_type,
            sql_key_candidate=_to_opt_str(item.get("sql_key_candidate")),
            header_row=_to_opt_pos_int(item.get("header_row")),
            template_row=_to_opt_pos_int(item.get("template_row")),
            key_fields=_to_str_list(item.get("key_fields")),
            columns=_to_str_list(item.get("columns")),
            category_field=_to_opt_str(item.get("category_field")),
            series_fields=_to_str_list(item.get("series_fields")),
            enabled=bool(item.get("enabled", True)),
            confidence=confidence,
            reason=str(item.get("reason", "")).strip(),
            notes=_to_str_list(item.get("notes")),
        )

        if not binding.shape_name:
            continue

        _apply_bind_type_defaults(binding)
        bindings.append(binding)

    return ReportMapDraft(
        generated_at=str(raw.get("generated_at", format_korean_now())),
        source_ppt=source_ppt,
        llm_provider=provider,
        llm_model=model,
        bindings=bindings,
    )


def _apply_bind_type_defaults(binding: MapDraftBinding) -> None:
    if binding.recommended_bind_type == "tbl" and binding.header_row is None:
        binding.header_row = 1
    if binding.recommended_bind_type == "tblr" and binding.template_row is None:
        binding.template_row = 2
    if binding.recommended_bind_type == "tblx":
        if binding.header_row is None:
            binding.header_row = 1
        if not binding.key_fields:
            binding.key_fields = ["FAM1", "USERFAM1", "DR"]
    if binding.recommended_bind_type == "cht" and not binding.series_fields:
        binding.series_fields = ["VALUE"]


# helpers

def _to_opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:  # pylint: disable=broad-except
        return default


def _to_opt_pos_int(value: Any) -> int | None:
    if value is None:
        return None
    parsed = _to_int(value, 0)
    return parsed if parsed > 0 else None


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:  # pylint: disable=broad-except
        return 0.5
