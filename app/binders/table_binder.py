"""정형표(tbl) 바인더 구현."""

from __future__ import annotations

import logging
from typing import Any

from app.models import ShapeBindingConfig
from app.ppt_session import PowerPointSession


class TableBinder:
    """tbl bind_type 처리기."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def bind(
        self,
        ppt: PowerPointSession,
        binding: ShapeBindingConfig,
        query_results: dict[str, list[dict[str, Any]]],
    ) -> str:
        if not binding.sql_key:
            raise ValueError(f"tbl 바인딩에는 sql_key가 필요합니다: {binding.shape_name}")

        rows = query_results.get(binding.sql_key, [])
        columns = binding.columns or (list(rows[0].keys()) if rows else [])
        if not columns:
            self.logger.warning("tbl 바인딩에 사용할 컬럼이 없습니다: %s", binding.shape_name)
            return f"tbl 바인딩 스킵({binding.shape_name}): 컬럼 없음"

        slide_index, shape = ppt.find_shape(binding.shape_name)
        if not ppt.is_table_shape(shape):
            raise ValueError(f"shape가 표가 아닙니다: {binding.shape_name}")

        table_rows, table_cols = ppt.table_size(shape)
        if table_cols < len(columns):
            raise ValueError(
                f"표 컬럼 수가 부족합니다: shape={binding.shape_name}, table_cols={table_cols}, required={len(columns)}"
            )

        header_row = binding.header_row
        data_start_row = header_row + 1

        for col_index, col_name in enumerate(columns, start=1):
            ppt.set_table_cell_text(shape, header_row, col_index, col_name)

        if binding.clear_existing and table_rows >= data_start_row:
            for row_index in range(data_start_row, table_rows + 1):
                for col_index in range(1, table_cols + 1):
                    ppt.set_table_cell_text(shape, row_index, col_index, "")

        writable_rows = max(0, table_rows - data_start_row + 1)
        to_write = min(writable_rows, len(rows))
        if len(rows) > writable_rows:
            self.logger.warning(
                "표 행이 부족하여 일부 데이터가 잘립니다: shape=%s total=%d writable=%d",
                binding.shape_name,
                len(rows),
                writable_rows,
            )

        for offset in range(to_write):
            data = rows[offset]
            row_index = data_start_row + offset
            for col_index, col_name in enumerate(columns, start=1):
                value = data.get(col_name)
                ppt.set_table_cell_text(shape, row_index, col_index, "" if value is None else str(value))

        self.logger.debug(
            "tbl binder 완료: slide=%s shape=%s rows=%d", slide_index, binding.shape_name, to_write
        )
        return f"tbl 채움 완료({binding.shape_name}): {to_write}행"
