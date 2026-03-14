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
    def is_table_shape(shape: Any) -> bool:
        return bool(getattr(shape, "HasTable", False))

    @staticmethod
    def get_table_cell_text(shape: Any, row: int, col: int) -> str:
        return str(shape.Table.Cell(row, col).Shape.TextFrame.TextRange.Text)

    @staticmethod
    def set_table_cell_text(shape: Any, row: int, col: int, text: str) -> None:
        shape.Table.Cell(row, col).Shape.TextFrame.TextRange.Text = text

    @staticmethod
    def table_size(shape: Any) -> tuple[int, int]:
        return int(shape.Table.Rows.Count), int(shape.Table.Columns.Count)

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
