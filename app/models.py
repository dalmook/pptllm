"""애플리케이션 전반에서 사용하는 데이터 모델 모음."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass(slots=True)
class AppPaths:
    """사용자가 GUI에서 선택한 주요 경로."""

    ppt_template: Path
    config_file: Path
    sql_dir: Path
    output_dir: Path


@dataclass(slots=True)
class AppConfig:
    """JSON 설정 파일에서 로드된 최소 설정 모델."""

    report_name: str
    db: Dict[str, str] = field(default_factory=dict)
    binders: Dict[str, List[str]] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionSummary:
    """1단계 실행 결과를 간단히 요약하기 위한 모델."""

    config_loaded: bool
    sql_files_count: int
    paths_verified: bool
    message: str
