"""Oracle DB 실행기."""

from __future__ import annotations

import logging
from typing import Any


class OracleExecutor:
    """oracledb 기반 쿼리 실행 래퍼."""

    def __init__(self, connection_info: dict[str, str], logger: logging.Logger) -> None:
        self.connection_info = connection_info
        self.logger = logger
        self._conn: Any | None = None

    def connect(self) -> None:
        """Oracle DB 연결을 연다."""

        try:
            import oracledb
        except ImportError as exc:
            raise RuntimeError(
                "oracledb 모듈을 찾을 수 없습니다. requirements 설치를 확인해 주세요."
            ) from exc

        self.logger.debug("Oracle 연결 시도: dsn=%s", self.connection_info.get("dsn", ""))
        try:
            self._conn = oracledb.connect(
                user=self.connection_info.get("user"),
                password=self.connection_info.get("password"),
                dsn=self.connection_info.get("dsn"),
            )
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(f"Oracle DB 연결에 실패했습니다: {exc}") from exc

    def query(self, sql: str) -> list[dict[str, Any]]:
        """SQL 실행 결과를 list[dict] 형태로 반환한다."""

        if self._conn is None:
            raise RuntimeError("DB 연결이 초기화되지 않았습니다. 먼저 connect()를 호출하세요.")

        try:
            cursor = self._conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description or []]
            rows = cursor.fetchall()
            result: list[dict[str, Any]] = [dict(zip(columns, row)) for row in rows]
            self.logger.debug("쿼리 결과 건수: %d", len(result))
            return result
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(f"SQL 실행 중 오류가 발생했습니다: {exc}") from exc
        finally:
            try:
                cursor.close()
            except Exception:  # pylint: disable=broad-except
                pass

    def close(self) -> None:
        """연결을 종료한다."""

        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def __enter__(self) -> "OracleExecutor":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
