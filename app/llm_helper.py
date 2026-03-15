"""LLM 기반 report_map/SQL 초안 생성 헬퍼."""

from __future__ import annotations

import json
import os
import re
import uuid
from abc import ABC, abstractmethod
from typing import Any

from app.json_validators import normalize_report_map_draft
from app.models import MapDraftBinding, PptShapeAnalysis, PptStructureReport, ReportMapDraft, SqlDraftResult
from app.prompt_builders import (
    build_map_generation_payload,
    build_map_generation_prompt,
    build_sql_generation_payload,
    build_sql_generation_prompt,
)
from app.utils.formatters import format_korean_now


class BaseProvider(ABC):
    """LLM provider 공통 인터페이스."""

    name: str
    model: str

    @abstractmethod
    def generate_map_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        pass

    @abstractmethod
    def generate_sql_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        pass


class MockProvider(BaseProvider):
    """LLM 없이 휴리스틱으로 draft를 생성하는 provider."""

    name = "mock"
    model = "mock-heuristic"

    def generate_map_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        bindings: list[dict[str, Any]] = []
        sql_keys: list[str] = payload.get("sql_keys", [])
        for shape in payload.get("shapes", []):
            bind_type, confidence, reason = self._recommend(shape)
            bindings.append(
                {
                    "shape_name": shape.get("shape_name", ""),
                    "slide_index": shape.get("slide_index", 0),
                    "recommended_bind_type": bind_type,
                    "sql_key_candidate": self._guess_sql_key(shape.get("shape_name", ""), sql_keys),
                    "header_row": (shape.get("header_row_candidates") or [1])[0] if bind_type in {"tbl", "tblx"} else None,
                    "template_row": 2 if bind_type == "tblr" else None,
                    "key_fields": ["FAM1", "USERFAM1", "DR"] if bind_type == "tblx" else [],
                    "columns": [],
                    "category_field": "MONTH" if bind_type == "cht" else None,
                    "series_fields": ["VALUE"] if bind_type == "cht" else [],
                    "enabled": bind_type != "none",
                    "confidence": confidence,
                    "reason": reason,
                    "notes": ["LLM 초안이며 반드시 사람이 검토해야 합니다."],
                }
            )
        return {"generated_at": format_korean_now(), "bindings": bindings}

    def generate_sql_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        bind_type = payload.get("bind_type", "none")
        sql_key = payload.get("sql_key_candidate") or payload.get("shape_name", "DRAFT_SQL").upper()
        cols = payload.get("columns") or []
        key_fields = payload.get("key_fields") or []
        category = payload.get("category_field") or "CATEGORY"
        series = payload.get("series_fields") or ["VALUE"]

        if bind_type == "tblx":
            expected = [*key_fields, "25.Q4", "26.Q1"] if key_fields else ["FAM1", "USERFAM1", "DR", "25.Q4", "26.Q1"]
            sql = (
                "SELECT\n"
                "  FAM1 AS FAM1, USERFAM1 AS USERFAM1, DR AS DR,\n"
                "  SUM(CASE WHEN QTR='25.Q4' THEN VAL END) AS \"25.Q4\",\n"
                "  SUM(CASE WHEN QTR='26.Q1' THEN VAL END) AS \"26.Q1\"\n"
                "FROM MST_SAMPLE\n"
                "GROUP BY FAM1, USERFAM1, DR"
            )
        elif bind_type == "tbl":
            expected = cols or ["COL1", "COL2"]
            select = ",\n  ".join([f"{c} AS {c}" for c in expected])
            sql = f"SELECT\n  {select}\nFROM MST_SAMPLE"
        elif bind_type == "tblr":
            expected = cols or ["ROWNUM", "FIELD"]
            sql = "SELECT\n  ROWNUM AS ROWNUM,\n  NAME AS FIELD\nFROM MST_SAMPLE"
        elif bind_type == "cht":
            expected = [category, *series]
            series_sql = ",\n  ".join([f"SUM({s}) AS {s}" for s in series])
            sql = f"SELECT\n  {category} AS {category},\n  {series_sql}\nFROM MST_SAMPLE\nGROUP BY {category}\nORDER BY {category}"
        else:
            expected = ["VALUE"]
            sql = "SELECT\n  SYSDATE AS VALUE\nFROM DUAL"

        return {
            "generated_at": format_korean_now(),
            "sql_key": sql_key,
            "confidence": 0.81,
            "assumptions": ["실제 테이블/필터는 검토 필요"],
            "notes": ["이 SQL은 초안이며 사람이 검토 후 사용해야 합니다."],
            "expected_output_columns": expected,
            "review_points": ["alias가 report_map과 일치하는지 확인"],
            "sql_text": sql,
        }

    def _recommend(self, shape: dict[str, Any]) -> tuple[str, float, str]:
        t = shape.get("shape_type")
        placeholders = shape.get("placeholder_candidates") or []
        anchors = shape.get("anchor_token_candidates") or []
        if t == "chart":
            return "cht", 0.92, "차트 shape"
        if t == "text" and placeholders:
            return "text", 0.9, "텍스트 placeholder"
        if t == "table" and anchors:
            return "tblx", 0.87, "anchor token 감지"
        if t == "table" and any("ROWNUM" in p or "FIELD" in p for p in placeholders):
            return "tblr", 0.82, "반복행 패턴"
        if t == "table":
            return "tbl", 0.75, "정형표"
        return "none", 0.45, "신호 부족"

    def _guess_sql_key(self, shape_name: str, sql_keys: list[str]) -> str | None:
        if not sql_keys:
            return None
        base = re.sub(r"[^a-z0-9]+", "_", shape_name.lower()).strip("_")
        for key in sql_keys:
            if key.lower() in base or base in key.lower():
                return key
        return sql_keys[0]


class OpenAICompatibleProvider(BaseProvider):
    """OpenAI SDK 기반 OpenAI-compatible provider."""

    name = "openai_compatible"

    def __init__(self, base_url: str, model: str, api_key: str, timeout_s: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_s = timeout_s
        self._response_json_mode = os.getenv("LLM_RESPONSE_JSON_MODE", "off").strip().lower()
        self._api_style = os.getenv("LLM_API_STYLE", "auto").strip().lower()

    def generate_map_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._chat_json(build_map_generation_prompt(payload))

    def generate_sql_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._chat_json(build_sql_generation_prompt(payload))

    def _chat_json(self, prompt: str) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai 패키지가 필요합니다. `pip install openai` 후 다시 시도하세요.") from exc

        client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout_s)
        errors: list[str] = []

        if self._api_style in {"auto", "responses"}:
            try:
                content = self._call_responses_api(client, prompt)
                return self._parse_content_json(content)
            except Exception as exc:  # pylint: disable=broad-except
                errors.append(f"responses API 실패: {exc}")
                if self._api_style == "responses":
                    raise RuntimeError("LLM 호출 실패: " + " | ".join(errors)) from exc

        if self._api_style in {"auto", "chat"}:
            try:
                content = self._call_chat_api(client, prompt)
                return self._parse_content_json(content)
            except Exception as exc:  # pylint: disable=broad-except
                errors.append(f"chat API 실패: {exc}")
                raise RuntimeError("LLM 호출 실패: " + " | ".join(errors)) from exc

        raise RuntimeError(f"LLM_API_STYLE 값이 올바르지 않습니다: {self._api_style}")

    def _call_chat_api(self, client: Any, prompt: str) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "JSON만 출력하세요."},
                {"role": "user", "content": prompt},
            ],
        }
        if self._response_json_mode == "on":
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        return str(resp.choices[0].message.content or "").strip()

    def _call_responses_api(self, client: Any, prompt: str) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": "JSON만 출력하세요."}]},
                {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
            ],
            "temperature": 0,
        }
        if self._response_json_mode == "on":
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.responses.create(**kwargs)
        content = getattr(resp, "output_text", "")
        if content:
            return str(content).strip()

        output = getattr(resp, "output", None) or []
        parts: list[str] = []
        for item in output:
            for c in getattr(item, "content", None) or []:
                text_value = getattr(c, "text", None)
                if isinstance(text_value, str) and text_value.strip():
                    parts.append(text_value.strip())
                elif hasattr(text_value, "value") and isinstance(text_value.value, str) and text_value.value.strip():
                    parts.append(text_value.value.strip())
        if not parts:
            raise RuntimeError("responses API 응답에서 텍스트를 찾지 못했습니다.")
        return "\n".join(parts)

    @staticmethod
    def _parse_content_json(content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            fence = re.search(r"```json\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
            if fence:
                return json.loads(fence.group(1))
            m = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if not m:
                raise RuntimeError("LLM 응답 JSON 파싱에 실패했습니다.")
            return json.loads(m.group(0))


class GptOssProvider(BaseProvider):
    """사내 GPT-OSS 게이트웨이 전용 provider (requests 기반)."""

    name = "gpt_oss"

    def __init__(self, api_url: str, credential_key: str, user_id: str, send_system_name: str, model: str, timeout_s: int = 60) -> None:
        self.api_url = api_url.strip()
        self.credential_key = credential_key.strip()
        self.user_id = user_id.strip()
        self.send_system_name = send_system_name.strip()
        self.model = model.strip()
        self.timeout_s = timeout_s

    def generate_map_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._chat_json(build_map_generation_prompt(payload))

    def generate_sql_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._chat_json(build_sql_generation_prompt(payload))

    def _chat_json(self, prompt: str) -> dict[str, Any]:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("requests 패키지가 필요합니다. `pip install requests` 후 다시 시도하세요.") from exc

        headers = {
            "x-dep-ticket": self.credential_key,
            "Send-System-Name": self.send_system_name,
            "User-Id": self.user_id,
            "User-Type": os.getenv("GPT_OSS_USER_TYPE", "AD_ID").strip() or "AD_ID",
            "Prompt-Msg-Id": str(uuid.uuid4()),
            "Completion-Msg-Id": str(uuid.uuid4()),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "JSON만 출력하세요."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1200")),
            "stream": False,
        }

        try:
            resp = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout_s)
            resp.raise_for_status()
            raw = resp.json()
            content = str(raw.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(f"GPT-OSS 호출 실패: {exc}") from exc

        return OpenAICompatibleProvider._parse_content_json(content)



class LLMHelper:
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
                raise ValueError("openai_compatible 사용 시 LLM_BASE_URL, LLM_MODEL, LLM_API_KEY가 필요합니다.")
            return cls(OpenAICompatibleProvider(base_url, model, api_key))
        if provider_name == "gpt_oss":
            api_url = os.getenv("GPT_OSS_API_URL", "").strip()
            credential_key = os.getenv("GPT_OSS_CREDENTIAL_KEY", "").strip()
            user_id = os.getenv("GPT_OSS_USER_ID", "").strip()
            send_system_name = os.getenv("GPT_OSS_SEND_SYSTEM_NAME", "").strip()
            model = os.getenv("GPT_OSS_MODEL", "openai/gpt-oss-120b").strip()
            if not api_url or not credential_key or not user_id or not send_system_name:
                raise ValueError(
                    "gpt_oss 사용 시 GPT_OSS_API_URL, GPT_OSS_CREDENTIAL_KEY, GPT_OSS_USER_ID, GPT_OSS_SEND_SYSTEM_NAME가 필요합니다."
                )
            return cls(GptOssProvider(api_url, credential_key, user_id, send_system_name, model))
        return cls(MockProvider())

    def generate_report_map_draft(self, structure: PptStructureReport, sql_keys: list[str], user_hints: str | None = None) -> ReportMapDraft:
        payload = build_map_generation_payload(structure=structure, sql_keys=sql_keys, user_hints=user_hints)
        raw = self.provider.generate_map_draft(payload)
        return normalize_report_map_draft(raw=raw, source_ppt=structure.template_file, provider=self.provider.name, model=self.provider.model)

    def generate_sql_draft(
        self,
        binding: MapDraftBinding,
        shape: PptShapeAnalysis | None,
        sql_keys: list[str],
        user_hint: dict[str, Any] | None = None,
    ) -> SqlDraftResult:
        payload = build_sql_generation_payload(binding=binding, shape=shape, sql_keys=sql_keys, user_hint=user_hint)
        raw = self.provider.generate_sql_draft(payload)
        return SqlDraftResult(
            generated_at=str(raw.get("generated_at", format_korean_now())),
            shape_name=binding.shape_name,
            sql_key=str(raw.get("sql_key", binding.sql_key_candidate or binding.shape_name)).upper(),
            bind_type=binding.recommended_bind_type,
            llm_provider=self.provider.name,
            llm_model=self.provider.model,
            confidence=float(raw.get("confidence", 0.5)),
            assumptions=[str(x) for x in raw.get("assumptions", [])],
            notes=[str(x) for x in raw.get("notes", [])],
            expected_output_columns=[str(x) for x in raw.get("expected_output_columns", [])],
            review_points=[str(x) for x in raw.get("review_points", [])],
            sql_text=str(raw.get("sql_text", "")),
            meta={
                "key_fields": binding.key_fields,
                "columns": binding.columns,
                "category_field": binding.category_field,
                "series_fields": binding.series_fields,
            },
        )

    def generate_sql_drafts_for_bindings(
        self,
        bindings: list[MapDraftBinding],
        shapes_by_name: dict[str, PptShapeAnalysis],
        sql_keys: list[str],
        hints_by_shape: dict[str, dict[str, Any]],
    ) -> list[SqlDraftResult]:
        out: list[SqlDraftResult] = []
        for b in bindings:
            out.append(self.generate_sql_draft(b, shapes_by_name.get(b.shape_name), sql_keys, hints_by_shape.get(b.shape_name)))
        return out

    # backward compatibility helpers
    def build_shape_analysis_payload(self, structure: PptStructureReport) -> dict[str, Any]:
        return build_map_generation_payload(structure, [])

    def build_map_generation_prompt(self, structure: PptStructureReport) -> str:
        return build_map_generation_prompt(build_map_generation_payload(structure, []))

    def build_sql_generation_prompt(self, payload: dict[str, Any]) -> str:
        return build_sql_generation_prompt(payload)
