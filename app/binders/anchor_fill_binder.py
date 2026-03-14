"""가로 확장 앵커 바인더(tblx) 스켈레톤."""

from __future__ import annotations

import logging
from typing import Any

from app.models import ShapeBindingConfig
from app.ppt_session import PowerPointSession


class AnchorFillBinder:
    """tblx bind_type 처리기 (2단계: 골격만 구현)."""

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
            "tblx는 현재 부분 구현 상태입니다. shape=%s, key_fields=%s",
            binding.shape_name,
            binding.key_fields,
        )
        # TODO:
        # 1) key_fields로 대상 1행 찾기
        # 2) 헤더 텍스트를 기준으로 컬럼 매핑
        # 3) 앵커 이후 오른쪽 셀 채움
        return f"tblx 스켈레톤 처리({binding.shape_name})"
