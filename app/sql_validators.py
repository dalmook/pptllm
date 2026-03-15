"""SQL 초안 검증기."""

from __future__ import annotations

import re
from typing import Iterable

from app.models import SqlDraftResult


def validate_sql_draft(draft: SqlDraftResult) -> tuple[str, list[str]]:
    warnings: list[str] = []
    sql = draft.sql_text.strip()
    if len(sql) < 20:
        return "failed", ["SQL 텍스트가 너무 짧습니다."]

    aliases = set(_extract_aliases(sql))

    if draft.bind_type == "tbl" and draft.expected_output_columns:
        missing = [c for c in draft.expected_output_columns if c not in aliases]
        if missing:
            warnings.append(f"tbl 필수 alias 누락: {missing}")

    if draft.bind_type == "tblx":
        kf = draft.meta.get("key_fields", [])
        if kf:
            missing_kf = [k for k in kf if k not in aliases]
            if missing_kf:
                warnings.append(f"tblx key_fields alias 누락: {missing_kf}")
        hdr = draft.expected_output_columns
        if hdr and all(h not in aliases for h in hdr):
            warnings.append("tblx 헤더 alias 후보를 찾지 못했습니다.")

    if draft.bind_type == "cht":
        if draft.meta.get("category_field") and draft.meta["category_field"] not in aliases:
            warnings.append("cht category_field alias 누락 가능")
        for s in draft.meta.get("series_fields", []):
            if s not in aliases:
                warnings.append(f"cht series alias 누락 가능: {s}")

    status = "warning" if warnings else "success"
    return status, warnings


def _extract_aliases(sql: str) -> Iterable[str]:
    pattern = re.compile(r"\bas\s+\"?([A-Za-z0-9_\.]+)\"?", flags=re.IGNORECASE)
    return [m.group(1) for m in pattern.finditer(sql)]
