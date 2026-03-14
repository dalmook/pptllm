"""문자열 포맷 관련 유틸리티."""

from __future__ import annotations

from datetime import datetime


def format_korean_now() -> str:
    """현재 시각을 한국어 표시용 문자열로 반환한다."""

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
