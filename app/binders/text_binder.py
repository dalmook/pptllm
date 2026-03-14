"""텍스트 placeholder 바인더 스켈레톤.

예: {{TODAY}}, {{SQLKEY__FIELD}}, {{SQLKEY__1__FIELD}}
"""

from __future__ import annotations


class TextBinder:
    """텍스트 치환 바인딩 인터페이스."""

    def bind(self) -> None:
        """TODO: placeholder 치환 구현."""

        return None
