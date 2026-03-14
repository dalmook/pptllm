"""LLM 연동을 위한 확장 인터페이스(미구현)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LLMRequest:
    """향후 프롬프트 구성에 사용할 요청 모델."""

    task: str
    context: str


class LLMHelper:
    """향후 LLM 연결을 담당할 헬퍼 인터페이스."""

    def summarize(self, request: LLMRequest) -> str:
        """요약 인터페이스(현재는 목업 응답)."""

        _ = request
        return "LLM 기능은 아직 비활성화 상태입니다."
