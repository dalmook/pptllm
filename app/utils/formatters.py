"""문자열/날짜/숫자 포맷 관련 유틸리티."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def format_korean_now() -> str:
    """현재 시각을 한국어 표시용 문자열로 반환한다."""

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_text() -> str:
    """TODAY placeholder 기본 문자열."""

    return date.today().strftime("%Y-%m-%d")


def normalize_text(text: str) -> str:
    """헤더/셀 비교를 위한 텍스트 정규화.

    - 앞뒤 공백 제거
    - 줄바꿈 제거
    - non-breaking space 제거
    """

    return text.replace("\xa0", " ").replace("\r", " ").replace("\n", " ").strip()


def to_display_text(value: Any) -> str:
    """COM 셀/텍스트에 쓸 문자열로 변환한다."""

    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def to_number_or_zero(value: Any) -> float:
    """차트용 숫자로 변환한다. 실패 시 0.0 반환."""

    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return 0.0
