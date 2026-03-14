"""반복행 템플릿 바인더(tblr) 스켈레톤."""

from __future__ import annotations

import logging
from typing import Any

from app.models import ShapeBindingConfig
from app.ppt_session import PowerPointSession


class RepeatRowBinder:
    """tblr bind_type 처리기 (2단계: 골격만 구현)."""

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
            "tblr는 현재 부분 구현 상태입니다. shape=%s, template_row=%d",
            binding.shape_name,
            binding.template_row,
        )
        # TODO:
        # 1) template_row 복제 로직 구현
        # 2) {{FIELD}}, {{ROWNUM}}, {{TODAY}} placeholder 치환
        # 3) 스타일/병합셀 보존 처리
        return f"tblr 스켈레톤 처리({binding.shape_name})"
