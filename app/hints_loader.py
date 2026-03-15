"""SQL 생성 힌트 로더."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_hints(hints_path: Path | None) -> dict[str, dict[str, Any]]:
    if hints_path is None or not hints_path.exists():
        return {}
    payload = json.loads(hints_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, val in payload.items():
        if isinstance(key, str) and isinstance(val, dict):
            out[key] = val
    return out
