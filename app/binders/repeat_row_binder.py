"""반복행 템플릿 바인더(tblr) 구현."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.models import ShapeBindingConfig
from app.ppt_session import PowerPointSession
from app.utils.formatters import to_display_text, today_text

_FIELD_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")


class RepeatRowBinder:
    """tblr bind_type 처리기."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def bind(
        self,
        ppt: PowerPointSession,
        binding: ShapeBindingConfig,
        query_results: dict[str, list[dict[str, Any]]],
    ) -> str:
        if not binding.sql_key:
            raise ValueError(f"tblr 바인딩에는 sql_key가 필요합니다: {binding.shape_name}")

        rows = query_results.get(binding.sql_key, [])
        slide_index, shape = ppt.find_shape(binding.shape_name)
        if not ppt.is_table_shape(shape):
            raise ValueError(f"shape가 표가 아닙니다: {binding.shape_name}")

        table_rows, table_cols = ppt.table_size(shape)
        template_row = binding.template_row
        if template_row < 1 or template_row > table_rows:
            raise ValueError(
                f"template_row가 표 범위를 벗어났습니다: shape={binding.shape_name}, template_row={template_row}"
            )

        if ppt.table_has_merge_risk(shape, template_row):
            self.logger.warning("병합 셀 가능성이 감지되었습니다. 결과가 예상과 다를 수 있습니다: %s", binding.shape_name)

        template_texts = [ppt.get_table_cell_text(shape, template_row, c) for c in range(1, table_cols + 1)]

        self.logger.debug(
            "tblr 시작: slide=%s shape=%s sql_key=%s result_rows=%d template_row=%d",
            slide_index,
            binding.shape_name,
            binding.sql_key,
            len(rows),
            template_row,
        )

        if not rows:
            return self._handle_empty_rows(ppt, shape, binding, template_texts)

        required_rows = len(rows)
        current_rows = ppt.table_size(shape)[0]
        while current_rows < template_row + required_rows - 1:
            insert_at = current_rows + 1
            ppt.add_table_row(shape, insert_at)
            ppt.clone_table_row_text(shape, template_row, insert_at)
            current_rows += 1

        for index, data in enumerate(rows, start=1):
            row_no = template_row + index - 1
            if row_no != template_row:
                ppt.clone_table_row_text(shape, template_row, row_no)
            for col_no, template_text in enumerate(template_texts, start=1):
                resolved = self._resolve_template_cell(template_text, data, index)
                ppt.set_table_cell_text(shape, row_no, col_no, resolved)

        return f"OK: tblr 채움 완료({binding.shape_name}) {len(rows)}행"

    def _handle_empty_rows(
        self,
        ppt: PowerPointSession,
        shape: Any,
        binding: ShapeBindingConfig,
        template_texts: list[str],
    ) -> str:
        if not binding.keep_template_row_if_empty:
            for col_no in range(1, len(template_texts) + 1):
                ppt.set_table_cell_text(shape, binding.template_row, col_no, "")
            self.logger.warning("tblr 결과 0건: 템플릿 행을 공백 처리했습니다. shape=%s", binding.shape_name)
            return f"WARN: tblr 결과 없음({binding.shape_name}) 템플릿 행 공백"

        if binding.clear_placeholders_if_empty:
            for col_no, template_text in enumerate(template_texts, start=1):
                cleared = self._resolve_template_cell(template_text, {}, 1)
                ppt.set_table_cell_text(shape, binding.template_row, col_no, cleared)
            self.logger.warning("tblr 결과 0건: placeholder만 정리했습니다. shape=%s", binding.shape_name)
            return f"WARN: tblr 결과 없음({binding.shape_name}) placeholder 정리"

        self.logger.warning("tblr 결과 0건: 템플릿 행 유지. shape=%s", binding.shape_name)
        return f"WARN: tblr 결과 없음({binding.shape_name})"

    def _resolve_template_cell(self, template_text: str, data: dict[str, Any], rownum: int) -> str:
        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key == "ROWNUM":
                return str(rownum)
            if key == "TODAY":
                return today_text()
            return to_display_text(data.get(key))

        return _FIELD_PATTERN.sub(_replace, template_text)
