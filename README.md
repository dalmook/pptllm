# PPT 보고서 자동화 도구 (5단계: LLM map 초안 생성기)

이번 단계에서는 LLM을 **실행 엔진이 아닌 설정 초안 생성기**로만 붙였습니다.
LLM은 PPT 수정/DB 조회/최종 실행 결정을 하지 않고, `ppt_structure`를 기반으로 `report_map.generated` 초안을 생성합니다.

> 생성 결과는 반드시 사람이 검토 후 반영해야 합니다.

## 핵심 기능

- 기존 실행 엔진 유지
  - 실행 결과: `output/debug_report.json`, `output/debug_report.md`
- 기존 구조 분석 유지
  - 구조 분석: `output/ppt_structure.json`, `output/ppt_structure.md`
- 신규 LLM map 초안 생성
  - `output/report_map.generated.json`
  - `output/report_map.generated.md`
- GUI에 `LLM으로 map 초안 생성` 버튼 추가
- LLM provider 2종 지원
  - `mock`
  - `openai_compatible`

## LLM provider 설정

`.env` 또는 환경변수로 설정합니다.

### 1) Mock provider (권장 기본값)
```cmd
set LLM_PROVIDER=mock
```

### 2) OpenAI-compatible provider
```cmd
set LLM_PROVIDER=openai_compatible
set LLM_BASE_URL=https://api.openai.com/v1
set LLM_MODEL=gpt-4o-mini
set LLM_API_KEY=YOUR_API_KEY
```

> 키/URL/모델은 하드코딩하지 않습니다.

`.env.example` 파일도 참고하세요.

## Windows CMD 실행

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

## GUI 사용 흐름

1. 템플릿 PPT 선택
2. config 선택
3. SQL 폴더 선택
4. output 폴더 선택
5. 버튼 실행
   - `실행`
   - `PPT 구조 분석`
   - `LLM으로 map 초안 생성`

## 생성 파일

- 실행
  - `debug_report.json`, `debug_report.md`
- 구조 분석
  - `ppt_structure.json`, `ppt_structure.md`
- LLM 초안 생성
  - `report_map.generated.json`, `report_map.generated.md`

## generated JSON 구조

```json
{
  "generated_at": "2026-03-15T20:00:00",
  "source_ppt": "C:\\reports\\template.pptx",
  "llm_provider": "mock",
  "llm_model": "mock-heuristic",
  "bindings": [
    {
      "shape_name": "tbl_pmix_qtr",
      "slide_index": 3,
      "recommended_bind_type": "tblx",
      "sql_key_candidate": "PMIX_QTR",
      "header_row": 1,
      "template_row": null,
      "key_fields": ["FAM1", "USERFAM1", "DR"],
      "columns": [],
      "category_field": null,
      "series_fields": [],
      "enabled": true,
      "confidence": 0.87,
      "reason": "anchor token 패턴으로 tblx를 추천합니다.",
      "notes": [
        "사람 검토 필요",
        "sql_key 후보는 shape 이름/SQL 파일명을 기준으로 추정"
      ]
    }
  ]
}
```

## 현재 한계/주의사항

- LLM 결과는 초안이며 정확성 보장 불가
- 자동으로 `report_map.json`을 덮어쓰지 않음
- OpenAI-compatible 호출 실패 시 환경변수/네트워크/응답 JSON 확인 필요
- COM 기반 실행/분석은 Windows + Office 환경에서 최종 검증 필요

## 다음 6단계 제안

- generated map -> 실행용 report_map 변환/병합 도구
- SQL 초안 생성기
- LLM 기반 오류 원인 문장형 진단

