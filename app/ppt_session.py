"""PowerPoint COM 세션 추상화(1단계 스켈레톤)."""

from __future__ import annotations

from pathlib import Path


class PowerPointSession:
    """pywin32 기반 PPT 자동화를 담당할 세션 클래스.

    1단계에서는 경로 확인 및 인터페이스만 제공한다.
    """

    def __init__(self, template_path: Path, output_dir: Path) -> None:
        self.template_path = template_path
        self.output_dir = output_dir

    def validate_paths(self) -> None:
        """PPT/출력 경로 유효성을 검증한다."""

        if not self.template_path.exists():
            raise FileNotFoundError(f"PowerPoint 템플릿 파일이 없습니다: {self.template_path}")
        if self.template_path.suffix.lower() not in {".pptx", ".pptm"}:
            raise ValueError("PowerPoint 템플릿은 .pptx 또는 .pptm 이어야 합니다.")

        if not self.output_dir.exists() or not self.output_dir.is_dir():
            raise FileNotFoundError(f"출력 폴더를 찾을 수 없습니다: {self.output_dir}")

    def run_mock_update(self) -> str:
        """1단계 목업 실행 결과 메시지를 반환한다."""

        return "PPT 바인딩은 다음 단계에서 구현 예정입니다. (현재: 실행 흐름 목업)"
