"""LLM 기반 report_map 초안 생성 오케스트레이터."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from app.models import ReportMapDraft
from app.report_writers import write_json_report, write_markdown_report


class MapGenerator:
    """생성된 map draft를 파일로 저장한다."""

    def write(self, output_dir: Path, draft: ReportMapDraft) -> tuple[Path, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "report_map.generated.json"
        md_path = output_dir / "report_map.generated.md"

        write_json_report(json_path, draft)
        write_markdown_report(md_path, self._to_markdown(draft))
        return json_path, md_path

    def _to_markdown(self, draft: ReportMapDraft) -> str:
        lines: list[str] = []
        lines.append("# report_map 초안 생성 결과")
        lines.append("")
        lines.append(f"- 생성 시각: {draft.generated_at}")
        lines.append(f"- Source PPT: `{draft.source_ppt}`")
        lines.append(f"- LLM Provider/Model: `{draft.llm_provider}` / `{draft.llm_model}`")
        lines.append("")

        lines.append("## 추천 바인딩 요약")
        lines.append("")
        lines.append("| Shape | Slide | Bind | SQL_KEY 후보 | Confidence | Reason |")
        lines.append("|---|---:|---|---|---:|---|")
        for b in draft.bindings:
            lines.append(
                f"| {b.shape_name} | {b.slide_index} | {b.recommended_bind_type} | "
                f"{b.sql_key_candidate or '-'} | {b.confidence:.2f} | {b.reason} |"
            )

        review_needed = [b for b in draft.bindings if b.confidence < 0.7 or b.recommended_bind_type == "none"]
        none_items = [b for b in draft.bindings if b.recommended_bind_type == "none"]

        lines.append("")
        lines.append("## 검토 필요 shape")
        lines.append("")
        if not review_needed:
            lines.append("- 없음")
        else:
            for b in review_needed:
                lines.append(f"- `{b.shape_name}` ({b.recommended_bind_type}, confidence={b.confidence:.2f})")

        lines.append("")
        lines.append("## none 분류 shape")
        lines.append("")
        if not none_items:
            lines.append("- 없음")
        else:
            for b in none_items:
                lines.append(f"- `{b.shape_name}`: {', '.join(b.notes) if b.notes else '추가 정보 필요'}")

        lines.append("")
        lines.append("## 상세 notes")
        lines.append("")
        for b in draft.bindings:
            if b.notes:
                lines.append(f"- `{b.shape_name}`")
                for note in b.notes:
                    lines.append(f"  - {note}")

        lines.append("")
        return "\n".join(lines)
