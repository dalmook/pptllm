"""텍스트 diff 유틸."""

from __future__ import annotations

import difflib


def make_unified_diff(old_text: str, new_text: str, from_name: str = "old", to_name: str = "new") -> str:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    return "".join(difflib.unified_diff(old_lines, new_lines, fromfile=from_name, tofile=to_name, n=2))
