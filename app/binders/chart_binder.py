"""차트 바인더(cht) 구현."""

from __future__ import annotations

import logging
from typing import Any

from app.models import ShapeBindingConfig
from app.ppt_session import PowerPointSession
from app.utils.formatters import to_display_text, to_number_or_zero


class ChartBinder:
    """cht bind_type 처리기."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def bind(
        self,
        ppt: PowerPointSession,
        binding: ShapeBindingConfig,
        query_results: dict[str, list[dict[str, Any]]],
    ) -> str:
        if not binding.sql_key:
            raise ValueError(f"cht 바인딩에는 sql_key가 필요합니다: {binding.shape_name}")
        if not binding.category_field:
            raise ValueError(f"cht 바인딩에는 category_field가 필요합니다: {binding.shape_name}")
        if not binding.series_fields:
            raise ValueError(f"cht 바인딩에는 series_fields가 필요합니다: {binding.shape_name}")

        rows = query_results.get(binding.sql_key, [])
        slide_index, shape = ppt.find_shape(binding.shape_name)
        if not ppt.is_chart_shape(shape):
            raise ValueError(f"shape가 차트가 아닙니다: {binding.shape_name}")

        self.logger.debug(
            "cht 시작: slide=%s shape=%s sql_key=%s rows=%d category=%s series=%s",
            slide_index,
            binding.shape_name,
            binding.sql_key,
            len(rows),
            binding.category_field,
            binding.series_fields,
        )

        data_rows: list[list[Any]] = []
        if not rows:
            if binding.clear_existing:
                ppt.update_chart_data(shape, binding.category_field, binding.series_fields, [])
                return f"WARN: cht 결과 없음({binding.shape_name}) 기존 데이터 초기화"
            self.logger.warning("cht 결과가 0건입니다: %s", binding.shape_name)
            return f"WARN: cht 결과 없음({binding.shape_name})"

        for row in rows:
            category = to_display_text(row.get(binding.category_field))
            values = [to_number_or_zero(row.get(series)) for series in binding.series_fields]
            data_rows.append([category, *values])

        ppt.update_chart_data(shape, binding.category_field, binding.series_fields, data_rows)
        return f"OK: cht 갱신 완료({binding.shape_name}) {len(data_rows)}행"
