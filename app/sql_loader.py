"""SQL 파일 스캔 및 로딩 유틸리티."""

from __future__ import annotations

from pathlib import Path
from typing import Dict


class SqlLoader:
    """SQL 폴더를 스캔하여 .sql 파일 목록을 수집한다."""

    def scan(self, sql_dir: Path) -> Dict[str, str]:
        """sql_dir 하위의 .sql 파일 내용을 읽어 딕셔너리로 반환한다.

        Returns:
            key: 확장자를 제외한 파일명
            value: SQL 문자열
        """

        if not sql_dir.exists() or not sql_dir.is_dir():
            raise FileNotFoundError(f"SQL 폴더를 찾을 수 없습니다: {sql_dir}")

        sql_map: Dict[str, str] = {}
        for file_path in sorted(sql_dir.glob("*.sql")):
            sql_map[file_path.stem] = file_path.read_text(encoding="utf-8")

        return sql_map
