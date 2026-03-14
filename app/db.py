"""Oracle 연결 추상화(1단계 스켈레톤)."""

from __future__ import annotations

from typing import Any, Dict, List


class OracleClient:
    """향후 실제 Oracle 조회를 담당할 클라이언트.

    1단계에서는 인터페이스만 제공하며, 실제 DB I/O는 수행하지 않는다.
    """

    def __init__(self, connection_info: Dict[str, str]) -> None:
        self.connection_info = connection_info

    def query(self, sql: str) -> List[Dict[str, Any]]:
        """SQL 실행 결과를 반환하는 자리.

        TODO: oracledb 기반 구현 연결.
        """

        _ = sql
        return []
