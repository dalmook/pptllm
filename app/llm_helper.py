"""LLM 연동 준비용 인터페이스(미호출)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.models import PptStructureReport, RunExecutionSummary


class LLMHelper:
    """다음 단계 LLM 연동에 사용할 payload/prompt builder."""

    def build_shape_analysis_payload(self, structure: PptStructureReport) -> dict[str, Any]:
        """shape 분석 payload를 반환한다(현재는 mock 구조화 데이터)."""

        return {
            "task": "shape_analysis",
            "structure_report": asdict(structure),
            "instruction": "recommended_bind_type를 기준으로 report_map 초안 생성 준비",
        }

    def build_map_generation_prompt(self, structure: PptStructureReport) -> str:
        """report_map 생성용 프롬프트 초안을 반환한다."""

        total = structure.total_shapes
        return (
            "다음 PPT 구조 분석 결과를 기반으로 report_map.json 초안을 생성하세요. "
            f"총 shape 수는 {total}개이며, 각 shape의 recommended_bind_type를 우선 반영하세요."
        )

    def build_sql_generation_prompt(self, run_summary: RunExecutionSummary) -> str:
        """SQL 초안 생성용 프롬프트 초안을 반환한다."""

        return (
            "다음 실행 요약에서 실패/경고 shape를 참고해 필요한 SQL_KEY 초안을 제안하세요. "
            f"성공={run_summary.success_count}, 경고={run_summary.warning_count}, 실패={run_summary.failure_count}."
        )
