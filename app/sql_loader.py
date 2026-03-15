"""SQL 파일 로더."""

from __future__ import annotations

import logging
from pathlib import Path


class SqlLoader:
    """sql 디렉터리에서 .sql 파일을 읽어 SQL_KEY 맵으로 반환한다."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def scan(self, sql_dir: Path) -> dict[str, str]:
        if not sql_dir.exists() or not sql_dir.is_dir():
            raise FileNotFoundError(f"SQL 폴더를 찾을 수 없습니다: {sql_dir}")

        sql_map: dict[str, str] = {}
        seen_casefold: set[str] = set()

        for file_path in sorted(sql_dir.glob("*.sql")):
            key = file_path.stem
            folded = key.casefold()
            if folded in seen_casefold:
                self.logger.warning("중복 SQL 키(대소문자 무시): %s", key)
                continue
            seen_casefold.add(folded)

            content = self._read_sql_file(file_path)
            if not content.strip():
                self.logger.warning("비어있는 SQL 파일입니다: %s", file_path.name)
                continue
            sql_map[key] = content

        if not sql_map:
            self.logger.warning("읽을 수 있는 SQL 파일이 없습니다: %s", sql_dir)

        self.logger.debug("SQL 로드 완료: keys=%s", list(sql_map.keys()))
        return sql_map

    def _read_sql_file(self, file_path: Path) -> str:
        for encoding in ("utf-8", "cp949"):
            try:
                text = file_path.read_text(encoding=encoding)
                if encoding == "cp949":
                    self.logger.debug("cp949로 SQL 파일을 읽었습니다: %s", file_path.name)
                return text
            except UnicodeDecodeError:
                continue
        raise ValueError(f"SQL 파일 인코딩을 읽을 수 없습니다(utf-8/cp949): {file_path}")
