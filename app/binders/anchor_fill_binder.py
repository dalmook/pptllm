"""가로 확장 앵커 바인더(tblx) 구현."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.models import ShapeBindingConfig
from app.ppt_session import PowerPointSession
from app.utils.formatters import normalize_text, to_display_text

_ANCHOR_PATTERN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


class AnchorFillBinder:
    """tblx bind_type 처리기."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def bind(
        self,
        ppt: PowerPointSession,
        binding: ShapeBindingConfig,
        query_results: dict[str, list[dict[str, Any]]],
    ) -> str:
        if not binding.sql_key:
            raise ValueError(f"tblx 바인딩에는 sql_key가 필요합니다: {binding.shape_name}")
        if not binding.key_fields:
            raise ValueError(f"tblx 바인딩에는 key_fields가 필요합니다: {binding.shape_name}")

        rows = query_results.get(binding.sql_key, [])
        slide_index, shape = ppt.find_shape(binding.shape_name)
        if not ppt.is_table_shape(shape):
            raise ValueError(f"shape가 표가 아닙니다: {binding.shape_name}")

        table_rows, table_cols = ppt.table_size(shape)
        header_row = binding.header_row
        if header_row < 1 or header_row > table_rows:
            raise ValueError(f"tblx header_row가 범위를 벗어났습니다: {binding.shape_name}")

        anchor_count = 0
        matched_count = 0
        empty_fill_count = 0

        self.logger.debug(
            "tblx 시작: slide=%s shape=%s sql_key=%s result_rows=%d key_fields=%s strict=%s",
            slide_index,
            binding.shape_name,
            binding.sql_key,
            len(rows),
            binding.key_fields,
            binding.strict_match,
        )

        for row_no in range(1, table_rows + 1):
            for col_no in range(1, table_cols + 1):
                cell_text = ppt.get_table_cell_text(shape, row_no, col_no)
                token_values = self._parse_anchor_token(cell_text)
                if token_values is None:
                    continue

                anchor_count += 1
                if len(token_values) != len(binding.key_fields):
                    self.logger.warning(
                        "anchor 토큰 개수와 key_fields 개수가 다릅니다: shape=%s token=%s key_fields=%s",
                        binding.shape_name,
                        token_values,
                        binding.key_fields,
                    )
                    continue

                matched_row = self._find_target_row(rows, binding.key_fields, token_values, binding.strict_match)
                if matched_row is None:
                    self._fill_right_with_blank(ppt, shape, row_no, col_no + 1, header_row, table_cols)
                    empty_fill_count += 1
                    continue

                matched_count += 1
                self._fill_right_with_data(ppt, shape, row_no, col_no + 1, header_row, table_cols, matched_row)

        if anchor_count == 0:
            return f"WARN: tblx anchor 미발견({binding.shape_name})"
        if matched_count == 0:
            return f"WARN: tblx 매칭 실패({binding.shape_name})"
        return (
            f"OK: tblx 채움 완료({binding.shape_name}) anchor={anchor_count} "
            f"match={matched_count} empty={empty_fill_count}"
        )

    def _parse_anchor_token(self, text: str) -> list[str] | None:
        match = _ANCHOR_PATTERN.fullmatch(text.strip())
        if not match:
            return None
        raw = match.group(1)
        return [normalize_text(part) for part in raw.split("|")]

    def _find_target_row(
        self,
        rows: list[dict[str, Any]],
        key_fields: list[str],
        token_values: list[str],
        strict_match: bool,
    ) -> dict[str, Any] | None:
        matched: list[dict[str, Any]] = []
        for row in rows:
            ok = True
            for key_field, token in zip(key_fields, token_values):
                if normalize_text(to_display_text(row.get(key_field))) != token:
                    ok = False
                    break
            if ok:
                matched.append(row)

        if not matched:
            self.logger.warning("tblx key_fields 매칭 결과가 없습니다: %s", token_values)
            return None

        if len(matched) > 1:
            message = f"tblx key_fields 매칭 결과가 {len(matched)}건입니다: {token_values}"
            if strict_match:
                raise ValueError(message)
            self.logger.warning("%s (첫 행 사용)", message)

        return matched[0]

    def _fill_right_with_data(
        self,
        ppt: PowerPointSession,
        shape: Any,
        target_row: int,
        start_col: int,
        header_row: int,
        table_cols: int,
        matched_row: dict[str, Any],
    ) -> None:
        for col_no in range(start_col, table_cols + 1):
            header = normalize_text(ppt.get_table_cell_text(shape, header_row, col_no))
            if not header:
                continue
            if header not in matched_row:
                continue
            ppt.set_table_cell_text(shape, target_row, col_no, to_display_text(matched_row.get(header)))

    def _fill_right_with_blank(
        self,
        ppt: PowerPointSession,
        shape: Any,
        target_row: int,
        start_col: int,
        header_row: int,
        table_cols: int,
    ) -> None:
        for col_no in range(start_col, table_cols + 1):
            header = normalize_text(ppt.get_table_cell_text(shape, header_row, col_no))
            if header:
                ppt.set_table_cell_text(shape, target_row, col_no, "")
