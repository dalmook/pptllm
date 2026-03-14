"""PPT 구조 분석기."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.models import PptShapeAnalysis, PptStructureReport
from app.ppt_session import PowerPointSession
from app.report_writers import write_json_report, write_markdown_report
from app.utils.formatters import format_korean_now, normalize_text

_PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")
_ANCHOR_RE = re.compile(r"\{\{\s*[^{}|]+\|[^{}]+\}\}")


class PptAnalyzer:
    """PowerPoint 템플릿 구조를 분석해 JSON/MD로 저장한다."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def analyze(self, template_path: Path, output_dir: Path) -> tuple[PptStructureReport, Path, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        report = PptStructureReport(
            analyzed_at=format_korean_now(),
            template_file=str(template_path),
            output_dir=str(output_dir),
            total_shapes=0,
            by_slide={},
        )

        with PowerPointSession(template_path=template_path, output_path=output_dir / "_analysis_tmp.pptx", logger=self.logger) as ppt:
            items = ppt.iter_shapes()
            report.total_shapes = len(items)
            for slide_index, shape in items:
                analyzed = self._analyze_shape(ppt, slide_index, shape)
                report.by_slide.setdefault(slide_index, []).append(analyzed)

        json_path = output_dir / "ppt_structure.json"
        md_path = output_dir / "ppt_structure.md"
        write_json_report(json_path, report)
        write_markdown_report(md_path, self._to_markdown(report))
        return report, json_path, md_path

    def _analyze_shape(self, ppt: PowerPointSession, slide_index: int, shape: Any) -> PptShapeAnalysis:
        shape_name = str(getattr(shape, "Name", ""))
        has_table = ppt.is_table_shape(shape)
        has_chart = ppt.is_chart_shape(shape)
        has_text = False
        text_preview = ""
        if not has_table and not has_chart:
            text = ppt.get_shape_text(shape)
            has_text = bool(normalize_text(text))
            text_preview = self._shorten(text)

        shape_type = "unknown"
        if has_chart:
            shape_type = "chart"
        elif has_table:
            shape_type = "table"
        elif has_text:
            shape_type = "text"

        table_rows = 0
        table_cols = 0
        table_preview: list[list[str]] = []
        placeholders: list[str] = []
        anchors: list[str] = []
        header_candidates: list[int] = []
        anchor_cells: list[str] = []
        chart_series_names: list[str] = []

        if has_table:
            table_rows, table_cols = ppt.table_size(shape)
            max_r, max_c = min(3, table_rows), min(8, table_cols)
            for r in range(1, max_r + 1):
                row_vals: list[str] = []
                non_empty = 0
                for c in range(1, max_c + 1):
                    cell = ppt.get_table_cell_text(shape, r, c)
                    row_vals.append(self._shorten(cell))
                    if normalize_text(cell):
                        non_empty += 1
                    placeholders.extend(_PLACEHOLDER_RE.findall(cell))
                    if _ANCHOR_RE.search(cell):
                        anchors.extend(_ANCHOR_RE.findall(cell))
                        anchor_cells.append(f"R{r}C{c}")
                if non_empty >= 2:
                    header_candidates.append(r)
                table_preview.append(row_vals)

        if has_chart:
            chart_series_names = self._get_chart_series_names(shape)

        if has_text and text_preview:
            placeholders.extend(_PLACEHOLDER_RE.findall(text_preview))
            if _ANCHOR_RE.search(text_preview):
                anchors.extend(_ANCHOR_RE.findall(text_preview))

        rec_bind, reason, rec_header, rec_template, key_hints = self._recommend(
            shape_type=shape_type,
            has_table=has_table,
            has_chart=has_chart,
            placeholders=placeholders,
            anchors=anchors,
            table_preview=table_preview,
            header_candidates=header_candidates,
        )

        return PptShapeAnalysis(
            shape_name=shape_name,
            slide_index=slide_index,
            shape_type=shape_type,
            has_text=has_text,
            text_preview=text_preview,
            has_table=has_table,
            table_rows=table_rows,
            table_cols=table_cols,
            header_row_candidates=header_candidates,
            table_preview=table_preview,
            has_chart=has_chart,
            chart_series_names=chart_series_names,
            placeholder_candidates=sorted(set(placeholders)),
            anchor_token_candidates=sorted(set(anchors)),
            recommended_bind_type=rec_bind,
            recommendation_reason=reason,
            recommended_header_row=rec_header,
            recommended_template_row=rec_template,
            recommended_key_fields_hints=key_hints,
            anchor_cell_candidates=anchor_cells,
        )

    def _recommend(
        self,
        shape_type: str,
        has_table: bool,
        has_chart: bool,
        placeholders: list[str],
        anchors: list[str],
        table_preview: list[list[str]],
        header_candidates: list[int],
    ) -> tuple[str, str, int | None, int | None, list[str]]:
        if has_chart:
            return "cht", "차트 shape로 감지되어 cht 바인딩을 권장합니다.", None, None, []

        if shape_type == "text" and placeholders:
            return "text", "텍스트 placeholder가 존재하여 text 바인딩을 권장합니다.", None, None, []

        if has_table:
            if anchors:
                return (
                    "tblx",
                    "테이블 셀에서 anchor token({{A|B|C}}) 패턴이 감지되어 tblx를 권장합니다.",
                    header_candidates[0] if header_candidates else 1,
                    None,
                    ["FAM1", "USERFAM1", "DR"],
                )
            if any("{{ROWNUM}}" in cell or "{{FIELD}}" in cell for row in table_preview for cell in row):
                return (
                    "tblr",
                    "반복행 placeholder 패턴이 감지되어 tblr를 권장합니다.",
                    None,
                    2,
                    [],
                )
            if placeholders:
                return "tblr", "테이블 내 placeholder가 있어 tblr 가능성이 높습니다.", None, 2, []
            return "tbl", "정형 테이블 구조로 보여 tbl 바인딩을 권장합니다.", header_candidates[0] if header_candidates else 1, None, []

        return "none", "바인딩 신호가 뚜렷하지 않아 수동 확인이 필요합니다.", None, None, []

    @staticmethod
    def _shorten(text: str, max_len: int = 120) -> str:
        normalized = normalize_text(text)
        return normalized[:max_len] + ("..." if len(normalized) > max_len else "")

    def _get_chart_series_names(self, shape: Any) -> list[str]:
        names: list[str] = []
        try:
            chart = shape.Chart
            series_collection = chart.SeriesCollection()
            count = int(series_collection.Count)
            for idx in range(1, count + 1):
                names.append(str(series_collection.Item(idx).Name))
        except Exception:  # pylint: disable=broad-except
            return names
        return names

    def _to_markdown(self, report: PptStructureReport) -> str:
        lines: list[str] = []
        lines.append("# PPT 구조 분석 리포트")
        lines.append("")
        lines.append(f"- 분석 시각: {report.analyzed_at}")
        lines.append(f"- 템플릿 파일: `{report.template_file}`")
        lines.append(f"- 총 shape 수: {report.total_shapes}")
        lines.append("")

        for slide_index in sorted(report.by_slide.keys()):
            lines.append(f"## Slide {slide_index}")
            lines.append("")
            lines.append("| Shape | Type | Text? | Table | Chart | 추천 bind | 추천 이유 |")
            lines.append("|---|---|---|---|---|---|---|")
            for shape in report.by_slide[slide_index]:
                lines.append(
                    f"| {shape.shape_name} | {shape.shape_type} | {shape.has_text} | "
                    f"{shape.table_rows}x{shape.table_cols if shape.has_table else 0} | {shape.has_chart} | "
                    f"{shape.recommended_bind_type} | {shape.recommendation_reason} |"
                )

                if shape.table_preview:
                    lines.append("")
                    lines.append(f"- `{shape.shape_name}` 표 preview")
                    for row in shape.table_preview:
                        lines.append(f"  - {row}")
                if shape.placeholder_candidates:
                    lines.append(f"- placeholder 후보: {shape.placeholder_candidates}")
                if shape.anchor_token_candidates:
                    lines.append(f"- anchor token 후보: {shape.anchor_token_candidates}")
                    lines.append(f"- anchor 셀 후보: {shape.anchor_cell_candidates}")
            lines.append("")

        return "\n".join(lines)
