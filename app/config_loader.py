"""report_map.json 로더 및 검증기."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models import ReportMap, ShapeBindingConfig

_ALLOWED_BIND_TYPES = {"text", "tbl", "tblr", "tblx", "cht"}


class ConfigLoader:
    """JSON 기반 리포트 매핑 설정을 로드한다."""

    def load(self, config_path: Path) -> ReportMap:
        """report_map.json 파일을 읽고 검증 후 모델로 반환한다."""

        if not config_path.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")

        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"설정 파일 JSON 형식이 올바르지 않습니다: {exc}") from exc

        report_name = self._as_required_str(payload, "report_name")
        output_prefix = self._as_optional_str(payload, "output_filename_prefix", default="report")

        db = payload.get("db")
        if not isinstance(db, dict):
            raise ValueError("설정 파일의 'db'는 객체여야 합니다.")
        for key in ("user", "password", "dsn"):
            if not isinstance(db.get(key), str) or not db.get(key).strip():
                raise ValueError(f"db.{key}는 비어있지 않은 문자열이어야 합니다.")

        raw_bindings = payload.get("bindings")
        if not isinstance(raw_bindings, list) or not raw_bindings:
            raise ValueError("설정 파일의 'bindings'는 1개 이상 항목을 가진 배열이어야 합니다.")

        bindings: list[ShapeBindingConfig] = []
        for index, raw in enumerate(raw_bindings, start=1):
            if not isinstance(raw, dict):
                raise ValueError(f"bindings[{index}] 항목은 객체여야 합니다.")
            bindings.append(self._parse_binding(raw, index))

        return ReportMap(
            report_name=report_name,
            db={"user": db["user"].strip(), "password": db["password"].strip(), "dsn": db["dsn"].strip()},
            output_filename_prefix=output_prefix,
            bindings=bindings,
        )

    def _parse_binding(self, raw: dict[str, Any], index: int) -> ShapeBindingConfig:
        shape_name = self._as_required_str(raw, "shape_name", f"bindings[{index}]")
        bind_type = self._as_required_str(raw, "bind_type", f"bindings[{index}]").lower()
        if bind_type not in _ALLOWED_BIND_TYPES:
            raise ValueError(
                f"bindings[{index}] bind_type이 올바르지 않습니다: {bind_type} "
                f"(허용값: {', '.join(sorted(_ALLOWED_BIND_TYPES))})"
            )

        sql_key = self._as_optional_str(raw, "sql_key", None)
        columns = self._as_str_list(raw.get("columns"), f"bindings[{index}].columns")
        key_fields = self._as_str_list(raw.get("key_fields"), f"bindings[{index}].key_fields")
        series_fields = self._as_str_list(raw.get("series_fields"), f"bindings[{index}].series_fields")

        header_row = int(raw.get("header_row", 1))
        template_row = int(raw.get("template_row", 2))
        if header_row < 1 or template_row < 1:
            raise ValueError(f"bindings[{index}]의 header_row/template_row는 1 이상이어야 합니다.")

        clear_existing = bool(raw.get("clear_existing", True))
        enabled = bool(raw.get("enabled", True))

        return ShapeBindingConfig(
            shape_name=shape_name,
            bind_type=bind_type,  # type: ignore[arg-type]
            sql_key=sql_key,
            columns=columns,
            header_row=header_row,
            template_row=template_row,
            key_fields=key_fields,
            category_field=self._as_optional_str(raw, "category_field", None),
            series_fields=series_fields,
            clear_existing=clear_existing,
            enabled=enabled,
        )

    @staticmethod
    def _as_required_str(payload: dict[str, Any], key: str, scope: str = "root") -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{scope}의 '{key}'는 비어있지 않은 문자열이어야 합니다.")
        return value.strip()

    @staticmethod
    def _as_optional_str(payload: dict[str, Any], key: str, default: str | None) -> str | None:
        value = payload.get(key, default)
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"'{key}'는 문자열이어야 합니다.")
        return value.strip()

    @staticmethod
    def _as_str_list(value: Any, field_name: str) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"{field_name}는 문자열 배열이어야 합니다.")
        for item in value:
            if not isinstance(item, str):
                raise ValueError(f"{field_name}는 문자열 배열이어야 합니다.")
        return [item.strip() for item in value if item.strip()]
