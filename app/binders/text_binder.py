"""텍스트 placeholder 바인더 구현.

지원 패턴:
- {{TODAY}}
- {{SQLKEY__FIELD}}
- {{SQLKEY__1__FIELD}}
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from app.models import ShapeBindingConfig
from app.ppt_session import PowerPointSession

_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_]+(?:__\d+__?[A-Za-z0-9_]+|__[A-Za-z0-9_]+)?)\s*\}\}")


class TextBinder:
    """text bind_type 처리기."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def bind(
        self,
        ppt: PowerPointSession,
        binding: ShapeBindingConfig,
        query_results: dict[str, list[dict[str, Any]]],
    ) -> str:
        """텍스트 shape/테이블 셀의 placeholder를 치환한다."""

        replaced_count = 0
        slide_index, shape = ppt.find_shape(binding.shape_name)
        self.logger.debug("text binder 시작: slide=%s shape=%s", slide_index, binding.shape_name)

        if ppt.is_table_shape(shape):
            rows, cols = ppt.table_size(shape)
            for row in range(1, rows + 1):
                for col in range(1, cols + 1):
                    raw = ppt.get_table_cell_text(shape, row, col)
                    new_text, cnt = self._replace_placeholders(raw, query_results)
                    if cnt:
                        ppt.set_table_cell_text(shape, row, col, new_text)
                        replaced_count += cnt
        else:
            raw = ppt.get_shape_text(shape)
            new_text, cnt = self._replace_placeholders(raw, query_results)
            if cnt:
                ppt.set_shape_text(shape, new_text)
                replaced_count += cnt

        return f"text 치환 완료({binding.shape_name}): {replaced_count}건"

    def _replace_placeholders(
        self,
        text: str,
        query_results: dict[str, list[dict[str, Any]]],
    ) -> tuple[str, int]:
        replaced_count = 0

        def _replace(match: re.Match[str]) -> str:
            nonlocal replaced_count
            token = match.group(1)
            value = self._resolve_token(token, query_results)
            if value is None:
                return match.group(0)
            replaced_count += 1
            return value

        return _PLACEHOLDER_PATTERN.sub(_replace, text), replaced_count

    def _resolve_token(
        self,
        token: str,
        query_results: dict[str, list[dict[str, Any]]],
    ) -> str | None:
        if token.upper() == "TODAY":
            return datetime.now().strftime("%Y-%m-%d")

        parts = token.split("__")
        if len(parts) == 2:
            sql_key, field = parts
            return self._get_field(query_results, sql_key, 1, field)

        if len(parts) == 3 and parts[1].isdigit():
            sql_key, row_num_text, field = parts
            return self._get_field(query_results, sql_key, int(row_num_text), field)

        self.logger.debug("지원하지 않는 placeholder 형식: %s", token)
        return None

    def _get_field(
        self,
        query_results: dict[str, list[dict[str, Any]]],
        sql_key: str,
        row_num: int,
        field: str,
    ) -> str:
        rows = query_results.get(sql_key, [])
        if row_num < 1 or row_num > len(rows):
            self.logger.debug("결과 행 범위 초과: sql_key=%s row_num=%s", sql_key, row_num)
            return ""

        row = rows[row_num - 1]
        if field not in row:
            self.logger.debug("필드 미존재: sql_key=%s field=%s", sql_key, field)
            return ""

        value = row[field]
        return "" if value is None else str(value)
