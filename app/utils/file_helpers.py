"""경로 유효성 검사 유틸리티."""

from __future__ import annotations

from pathlib import Path


def ensure_file(path: Path, name: str) -> None:
    """파일 존재 여부를 검사한다."""

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"{name} 파일을 찾을 수 없습니다: {path}")


def ensure_dir(path: Path, name: str) -> None:
    """디렉터리 존재 여부를 검사한다."""

    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"{name} 폴더를 찾을 수 없습니다: {path}")
