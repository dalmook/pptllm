"""JSON/Markdown 리포트 저장 공통 유틸."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def _to_serializable(data: Any) -> Any:
    if is_dataclass(data):
        return {k: _to_serializable(v) for k, v in asdict(data).items()}
    if isinstance(data, dict):
        return {str(k): _to_serializable(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_to_serializable(v) for v in data]
    return data


def write_json_report(path: Path, data: Any) -> Path:
    """JSON 리포트를 저장한다."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _to_serializable(data)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_markdown_report(path: Path, markdown_text: str) -> Path:
    """Markdown 리포트를 저장한다."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown_text, encoding="utf-8")
    return path


def build_output_file(base_dir: Path, filename: str) -> Path:
    """출력 폴더 기준 파일 경로를 생성한다."""

    return base_dir / filename
