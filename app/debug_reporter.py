"""실행 디버그 리포트 생성기."""

from __future__ import annotations

from pathlib import Path

from app.models import RunExecutionSummary
from app.report_writers import write_json_report, write_markdown_report


class DebugReporter:
    """실행 결과를 JSON/Markdown으로 저장한다."""

    def write(self, output_dir: Path, summary: RunExecutionSummary) -> tuple[Path, Path]:
        json_path = output_dir / "debug_report.json"
        md_path = output_dir / "debug_report.md"
        write_json_report(json_path, summary)
        write_markdown_report(md_path, self._to_markdown(summary))
        return json_path, md_path

    def _to_markdown(self, summary: RunExecutionSummary) -> str:
        fail_items = [s for s in summary.shape_results if s.status == "failed"]
        warn_items = [s for s in summary.shape_results if s.status == "warning"]

        lines: list[str] = []
        lines.append("# 실행 디버그 리포트")
        lines.append("")
        lines.append(f"- 실행 시각: {summary.executed_at}")
        lines.append(f"- 템플릿 파일: `{summary.template_file}`")
        lines.append(f"- output 파일: `{summary.output_file}`")
        lines.append(f"- config 파일: `{summary.config_file}`")
        lines.append(f"- sql 폴더: `{summary.sql_dir}`")
        lines.append("")
        lines.append("## 전체 요약")
        lines.append("")
        lines.append("| 성공 | 경고 | 실패 | 건너뜀 | 총 소요(ms) |")
        lines.append("|---:|---:|---:|---:|---:|")
        lines.append(
            f"| {summary.success_count} | {summary.warning_count} | {summary.failure_count} "
            f"| {summary.skipped_count} | {summary.total_elapsed_ms} |"
        )
        lines.append("")
        lines.append("## SQL row_count 요약")
        lines.append("")
        lines.append("| SQL_KEY | Row Count |")
        lines.append("|---|---:|")
        for key in summary.loaded_sql_keys:
            lines.append(f"| {key} | {summary.sql_row_counts.get(key, 0)} |")
        lines.append("")
        lines.append("## shape별 결과")
        lines.append("")
        lines.append("| Shape | Type | Bind | SQL_KEY | Status | Row | 시간(ms) | 메시지 |")
        lines.append("|---|---|---|---|---|---:|---:|---|")
        for item in summary.shape_results:
            lines.append(
                f"| {item.shape_name} | {item.shape_type} | {item.bind_type} | {item.sql_key or '-'} "
                f"| {item.status} | {item.row_count} | {item.elapsed_ms} | {item.message} |"
            )
        lines.append("")

        lines.append("## 실패 목록")
        lines.append("")
        if not fail_items:
            lines.append("- 없음")
        else:
            for item in fail_items:
                lines.append(f"- `{item.shape_name}`: {item.message}")
        lines.append("")

        lines.append("## 경고 목록")
        lines.append("")
        if not warn_items:
            lines.append("- 없음")
        else:
            for item in warn_items:
                lines.append(f"- `{item.shape_name}`: {item.message}")
        lines.append("")

        lines.append("## 성능 요약")
        lines.append("")
        lines.append(f"- 총 수행 시간: {summary.total_elapsed_ms} ms")
        for item in summary.shape_results:
            lines.append(f"- {item.shape_name}: {item.elapsed_ms} ms")

        if summary.exception_message:
            lines.append("")
            lines.append("## 예외 정보")
            lines.append("")
            lines.append(f"- 메시지: {summary.exception_message}")
            if summary.stack_trace:
                lines.append("")
                lines.append("```text")
                lines.append(summary.stack_trace)
                lines.append("```")

        lines.append("")
        return "\n".join(lines)
