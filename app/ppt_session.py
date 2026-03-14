"""PowerPoint COM 세션 도우미."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any


class PowerPointSession:
    """pywin32 COM 자동화 세션."""

    def __init__(self, template_path: Path, output_path: Path, logger: logging.Logger) -> None:
        self.template_path = template_path
        self.output_path = output_path
        self.logger = logger
        self.app: Any | None = None
        self.presentation: Any | None = None

    def open(self) -> None:
        """PowerPoint를 열고 템플릿 파일을 로드한다."""

        self._validate_paths()
        try:
            import win32com.client
        except ImportError as exc:
            raise RuntimeError(
                "pywin32(win32com) 모듈을 찾을 수 없습니다. Windows 환경과 requirements를 확인해 주세요."
            ) from exc

        try:
            self.app = win32com.client.Dispatch("PowerPoint.Application")
            self.app.Visible = True
            self.presentation = self.app.Presentations.Open(str(self.template_path), WithWindow=False)
            self.logger.info("PPT 템플릿을 열었습니다: %s", self.template_path)
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(f"PowerPoint 파일 열기에 실패했습니다: {exc}") from exc

    def save_as_output(self) -> None:
        """결과를 output 파일로 저장한다."""

        if self.presentation is None:
            raise RuntimeError("PPT 세션이 열려 있지 않습니다.")

        try:
            self.presentation.SaveAs(str(self.output_path))
            self.logger.info("결과 파일 저장 완료: %s", self.output_path)
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(f"결과 파일 저장에 실패했습니다: {exc}") from exc

    def close(self) -> None:
        """COM 객체를 안전하게 정리한다."""

        if self.presentation is not None:
            try:
                self.presentation.Close()
            except Exception:  # pylint: disable=broad-except
                pass
            self.presentation = None

        if self.app is not None:
            try:
                self.app.Quit()
            except Exception:  # pylint: disable=broad-except
                pass
            self.app = None

    def iter_shapes(self) -> list[tuple[int, Any]]:
        """(slide_index, shape) 목록을 반환한다."""

        if self.presentation is None:
            raise RuntimeError("PPT 세션이 열려 있지 않습니다.")

        items: list[tuple[int, Any]] = []
        for slide_index, slide in enumerate(self.presentation.Slides, start=1):
            for shape in slide.Shapes:
                items.append((slide_index, shape))
        return items

    def find_shape(self, shape_name: str) -> tuple[int, Any]:
        """이름으로 shape를 찾는다."""

        for slide_index, shape in self.iter_shapes():
            if str(shape.Name).strip() == shape_name:
                return slide_index, shape
        raise ValueError(f"PPT에서 shape를 찾을 수 없습니다: {shape_name}")

    @staticmethod
    def get_shape_text(shape: Any) -> str:
        if shape.HasTextFrame and shape.TextFrame.HasText:
            return str(shape.TextFrame.TextRange.Text)
        return ""

    @staticmethod
    def set_shape_text(shape: Any, text: str) -> None:
        if not shape.HasTextFrame:
            raise ValueError("텍스트 프레임이 없는 shape에는 텍스트를 쓸 수 없습니다.")
        shape.TextFrame.TextRange.Text = text


    @staticmethod
    def detect_shape_type(shape: Any) -> str:
        if bool(getattr(shape, "HasChart", False)):
            return "chart"
        if bool(getattr(shape, "HasTable", False)):
            return "table"
        if bool(getattr(shape, "HasTextFrame", False)) and bool(getattr(shape.TextFrame, "HasText", False)):
            return "text"
        return "unknown"

    @staticmethod
    def is_table_shape(shape: Any) -> bool:
        return bool(getattr(shape, "HasTable", False))

    @staticmethod
    def is_chart_shape(shape: Any) -> bool:
        return bool(getattr(shape, "HasChart", False))

    @staticmethod
    def get_table_cell_text(shape: Any, row: int, col: int) -> str:
        return str(shape.Table.Cell(row, col).Shape.TextFrame.TextRange.Text)

    @staticmethod
    def set_table_cell_text(shape: Any, row: int, col: int, text: str) -> None:
        shape.Table.Cell(row, col).Shape.TextFrame.TextRange.Text = text

    @staticmethod
    def table_size(shape: Any) -> tuple[int, int]:
        return int(shape.Table.Rows.Count), int(shape.Table.Columns.Count)

    @staticmethod
    def add_table_row(shape: Any, row_index: int) -> None:
        shape.Table.Rows.Add(row_index)

    def clone_table_row_text(self, shape: Any, source_row: int, target_row: int) -> None:
        """행의 셀 텍스트를 복제한다(서식은 COM 기본 동작에 의존)."""

        _, cols = self.table_size(shape)
        for col in range(1, cols + 1):
            try:
                src = self.get_table_cell_text(shape, source_row, col)
                self.set_table_cell_text(shape, target_row, col, src)
            except Exception:  # pylint: disable=broad-except
                continue

    def table_has_merge_risk(self, shape: Any, row: int) -> bool:
        """병합 셀로 인한 위험 징후를 간단히 탐지한다."""

        _, cols = self.table_size(shape)
        for col in range(1, cols + 1):
            try:
                _ = shape.Table.Cell(row, col)
            except Exception:  # pylint: disable=broad-except
                return True
        return False

    def update_chart_data(self, shape: Any, category_name: str, series_names: list[str], rows: list[list[Any]]) -> None:
        """차트 데이터시트를 열어 category + series 데이터를 교체한다."""

        chart = shape.Chart
        chart.ChartData.Activate()
        workbook = chart.ChartData.Workbook
        worksheet = workbook.Worksheets(1)

        max_rows = max(2, len(rows) + 1)
        max_cols = max(2, len(series_names) + 1)

        for r in range(1, 300):
            for c in range(1, 30):
                worksheet.Cells(r, c).Value = None

        worksheet.Cells(1, 1).Value = category_name
        for index, series_name in enumerate(series_names, start=2):
            worksheet.Cells(1, index).Value = series_name

        for row_index, data_row in enumerate(rows, start=2):
            for col_index, value in enumerate(data_row, start=1):
                worksheet.Cells(row_index, col_index).Value = value

        end_col = chr(ord("A") + max_cols - 1)
        chart.SetSourceData(f"=Sheet1!$A$1:${end_col}${max_rows}")
        workbook.Application.Quit()

    def _validate_paths(self) -> None:
        if not self.template_path.exists():
            raise FileNotFoundError(f"PowerPoint 템플릿 파일이 없습니다: {self.template_path}")
        if self.template_path.suffix.lower() not in {".pptx", ".pptm"}:
            raise ValueError("PowerPoint 템플릿은 .pptx 또는 .pptm 이어야 합니다.")
        if not self.output_path.parent.exists():
            raise FileNotFoundError(f"출력 폴더를 찾을 수 없습니다: {self.output_path.parent}")

    def __enter__(self) -> "PowerPointSession":
        self.open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
