"""차트 바인더(cht) 스켈레톤."""

from __future__ import annotations

import logging
from typing import Any

from app.models import ShapeBindingConfig
from app.ppt_session import PowerPointSession


class ChartBinder:
    """cht bind_type 처리기 (2단계: 골격만 구현)."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def bind(
        self,
        ppt: PowerPointSession,
        binding: ShapeBindingConfig,
        query_results: dict[str, list[dict[str, Any]]],
    ) -> str:
        _ = (ppt, query_results)
        self.logger.info(
            "cht는 현재 부분 구현 상태입니다. shape=%s, category_field=%s",
            binding.shape_name,
            binding.category_field,
        )
        # TODO:
        # 1) category_field + series_fields 기반 데이터셋 생성
        # 2) 차트 데이터시트 업데이트
        # 3) clear_existing 옵션 반영
        return f"cht 스켈레톤 처리({binding.shape_name})"
