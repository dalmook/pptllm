"""JSON 설정 파일 로더."""

from __future__ import annotations

import json
from pathlib import Path

from app.models import AppConfig


class ConfigLoader:
    """보고서 매핑 설정(JSON)을 로드하고 검증한다."""

    def load(self, config_path: Path) -> AppConfig:
        """설정 파일을 읽어 AppConfig로 반환한다.

        Args:
            config_path: 설정 JSON 파일 경로

        Raises:
            FileNotFoundError: 파일이 없는 경우
            ValueError: JSON 형식 또는 필수 키 누락 시
        """

        if not config_path.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")

        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"설정 파일 JSON 형식이 올바르지 않습니다: {exc}") from exc

        report_name = payload.get("report_name")
        if not report_name:
            raise ValueError("설정 파일에 'report_name'이 필요합니다.")

        return AppConfig(
            report_name=report_name,
            db=payload.get("db", {}),
            binders=payload.get("binders", {}),
        )
