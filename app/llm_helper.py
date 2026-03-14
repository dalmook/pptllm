"""LLM 기반 report_map 초안 생성 헬퍼."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import Any

from app.json_validators import normalize_report_map_draft
from app.models import PptShapeAnalysis, PptStructureReport, ReportMapDraft
from app.prompt_builders import build_map_generation_payload, build_map_generation_prompt
from app.utils.formatters import format_korean_now


class BaseProvider(ABC):
    """LLM provider 인터페이스."""

    name: str
    model: str

    @abstractmethod
    def generate_map_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        """map 초안 raw JSON(dict)을 반환한다."""


class MockProvider(BaseProvider):
    """LLM 없이 휴리스틱으로 draft를 생성하는 provider."""

    name = "mock"
    model = "mock-heuristic"

    def generate_map_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        bindings: list[dict[str, Any]] = []
        sql_keys: list[str] = payload.get("sql_keys", [])

        for shape in payload.get("shapes", []):
            bind_type, confidence, reason = self._recommend(shape)
            sql_candidate = self._guess_sql_key(shape.get("shape_name", ""), sql_keys)
            binding = {
                "shape_name": shape.get("shape_name", ""),
                "slide_index": shape.get("slide_index", 0),
                "recommended_bind_type": bind_type,
                "sql_key_candidate": sql_candidate,
                "header_row": (shape.get("header_row_candidates") or [1])[0] if bind_type in {"tbl", "tblx"} else None,
                "template_row": 2 if bind_type == "tblr" else None,
                "key_fields": ["FAM1", "USERFAM1", "DR"] if bind_type == "tblx" else [],
                "columns": [],
                "category_field": "MONTH" if bind_type == "cht" else None,
                "series_fields": ["VALUE"] if bind_type == "cht" else [],
                "enabled": bind_type != "none",
                "confidence": confidence,
                "reason": reason,
                "notes": [
                    "이 결과는 LLM 초안이며 사람이 검토 후 확정해야 합니다.",
                    "sql_key_candidate와 header/template 값은 추정치입니다.",
                ],
            }
            bindings.append(binding)

        return {
            "generated_at": format_korean_now(),
            "bindings": bindings,
        }

    def _recommend(self, shape: dict[str, Any]) -> tuple[str, float, str]:
        shape_type = shape.get("shape_type")
        placeholders = shape.get("placeholder_candidates") or []
        anchors = shape.get("anchor_token_candidates") or []

        if shape_type == "chart":
            return "cht", 0.92, "차트 shape로 분석되어 cht를 추천합니다."
        if shape_type == "text" and placeholders:
            return "text", 0.9, "텍스트 placeholder가 존재해 text를 추천합니다."
        if shape_type == "table" and anchors:
            return "tblx", 0.87, "표 내 anchor token 패턴이 있어 tblx를 추천합니다."
        if shape_type == "table" and any("ROWNUM" in p or "FIELD" in p for p in placeholders):
            return "tblr", 0.82, "반복행 placeholder 패턴으로 tblr를 추천합니다."
        if shape_type == "table":
            return "tbl", 0.75, "정형 테이블 형태로 보여 tbl을 추천합니다."
        return "none", 0.45, "바인딩 신호가 부족합니다."

    def _guess_sql_key(self, shape_name: str, sql_keys: list[str]) -> str | None:
        if not sql_keys:
            return None
        base = re.sub(r"[^a-z0-9]+", "_", shape_name.lower()).strip("_")
        for key in sql_keys:
            if key.lower() in base or base in key.lower():
                return key
        return sql_keys[0]


class OpenAICompatibleProvider(BaseProvider):
    """OpenAI-compatible endpoint provider."""

    name = "openai_compatible"

    def __init__(self, base_url: str, model: str, api_key: str, timeout_s: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_s = timeout_s

    def generate_map_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = build_map_generation_prompt(payload)
        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "당신은 report_map 초안을 생성하는 도우미입니다."},
                {"role": "user", "content": prompt},
            ],
        }

        req = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"LLM 호출 HTTP 오류: {exc.code} {exc.reason}") from exc
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(f"LLM 호출 실패: {exc}") from exc

        content = self._extract_content(raw)
        return self._parse_content_json(content)

    @staticmethod
    def _extract_content(response: dict[str, Any]) -> str:
        try:
            return str(response["choices"][0]["message"]["content"])
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError("LLM 응답에서 content를 찾지 못했습니다.") from exc

    @staticmethod
    def _parse_content_json(content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # fence fallback
            m = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if not m:
                raise RuntimeError("LLM 응답 JSON 파싱에 실패했습니다.")
            return json.loads(m.group(0))


class LLMHelper:
    """provider 선택 + draft 생성 orchestration."""

    def __init__(self, provider: BaseProvider) -> None:
        self.provider = provider

    @classmethod
    def from_env(cls) -> "LLMHelper":
        provider_name = os.getenv("LLM_PROVIDER", "mock").strip().lower()
        if provider_name == "openai_compatible":
            base_url = os.getenv("LLM_BASE_URL", "").strip()
            model = os.getenv("LLM_MODEL", "").strip()
            api_key = os.getenv("LLM_API_KEY", "").strip()
            if not base_url or not model or not api_key:
                raise ValueError(
                    "openai_compatible 사용 시 LLM_BASE_URL, LLM_MODEL, LLM_API_KEY 환경변수가 필요합니다."
                )
            return cls(OpenAICompatibleProvider(base_url=base_url, model=model, api_key=api_key))

        return cls(MockProvider())

    def generate_report_map_draft(
        self,
        structure: PptStructureReport,
        sql_keys: list[str],
        user_hints: str | None = None,
    ) -> ReportMapDraft:
        payload = build_map_generation_payload(structure=structure, sql_keys=sql_keys, user_hints=user_hints)
        raw = self.provider.generate_map_draft(payload)
        draft = normalize_report_map_draft(
            raw=raw,
            source_ppt=structure.template_file,
            provider=self.provider.name,
            model=self.provider.model,
        )
        return draft

    # 기존 인터페이스 호환
    def build_shape_analysis_payload(self, structure: PptStructureReport) -> dict[str, Any]:
        return build_map_generation_payload(structure=structure, sql_keys=[])

    def build_map_generation_prompt(self, structure: PptStructureReport) -> str:
        payload = build_map_generation_payload(structure=structure, sql_keys=[])
        return build_map_generation_prompt(payload)

    def build_sql_generation_prompt(self, run_summary: Any) -> str:
        return (
            "다음 실행 요약에서 실패/경고 shape를 참고해 필요한 SQL_KEY 초안을 제안하세요. "
            f"성공={getattr(run_summary, 'success_count', 0)}, "
            f"경고={getattr(run_summary, 'warning_count', 0)}, 실패={getattr(run_summary, 'failure_count', 0)}."
        )
