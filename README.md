# PPT 보고서 자동화 도구 (6단계: LLM SQL 초안 생성기)

이번 단계에서는 LLM 역할을 확장해 **report_map 초안 + SQL 초안 생성**을 지원합니다.
단, LLM은 여전히 실행 엔진이 아니며, 생성 결과는 반드시 사람이 검토 후 사용해야 합니다.

## 핵심 기능

- 기존 실행 엔진/구조 분석/디버그 리포트 유지
- LLM map 초안 생성
  - `output/report_map.generated.json`
  - `output/report_map.generated.md`
- LLM SQL 초안 생성 (신규)
  - `output/sql_drafts/{SQL_KEY}.sql`
  - `output/sql_drafts/{SQL_KEY}.md`
- 기존 `sql/*.sql` 자동 overwrite 금지 (draft 폴더로만 저장)

## LLM Provider 설정

### Mock provider (기본)
```cmd
set LLM_PROVIDER=mock
```

### OpenAI-compatible provider
```cmd
set LLM_PROVIDER=openai_compatible
set LLM_BASE_URL=https://api.openai.com/v1
set LLM_MODEL=gpt-4o-mini
set LLM_API_KEY=YOUR_API_KEY
set LLM_API_STYLE=auto
```

- `LLM_API_STYLE`
  - `auto`(기본): `responses` 호출을 먼저 시도하고 실패 시 `chat.completions`로 fallback
  - `responses`: `gpt_oss_example.py`와 유사한 Responses API만 사용
  - `chat`: Chat Completions API만 사용

`.env.example` 참고.


### GPT-OSS gateway provider
```cmd
set LLM_PROVIDER=gpt_oss
set GPT_OSS_API_URL=http://apigw.samsungds.net:8000/gpt-oss/1/gpt-oss-120b/v1/chat/completions
set GPT_OSS_CREDENTIAL_KEY=credential:...
set GPT_OSS_USER_ID=your.adid
set GPT_OSS_USER_TYPE=AD_ID
set GPT_OSS_SEND_SYSTEM_NAME=GOC_MAIL_RAG_PIPELINE
set GPT_OSS_MODEL=openai/gpt-oss-120b
```

제공해주신 `gpt_oss_example.py`와 동일하게 `x-dep-ticket`, `Send-System-Name`, `User-Id`, `User-Type`, `Prompt-Msg-Id`, `Completion-Msg-Id` 헤더를 사용해 호출합니다.


## Windows CMD 실행

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```


## Oracle 연결 설정

DB 연결값은 기본적으로 `config/report_map.json`의 `db` 섹션을 사용합니다.
아래 환경변수를 설정하면 같은 키를 **우선 override** 하도록 지원합니다.

```cmd
set ORACLE_HOST=gmgsdd09-vip.sec.samsung.net
set ORACLE_PORT=2541
set ORACLE_SERVICE=MEMSCM
set ORACLE_USER=memscm
set ORACLE_PW=mem01scm
```

- `ORACLE_DSN`을 직접 지정할 수도 있습니다. (예: `HOST:PORT/SERVICE`)
- `ORACLE_DSN`이 없으면 `ORACLE_HOST/ORACLE_PORT/ORACLE_SERVICE`를 조합해 DSN을 만듭니다.
- 환경변수가 비어 있으면 `report_map.json`의 `db.user/password/dsn` 값이 사용됩니다.

## GUI 버튼

- 실행
- PPT 구조 분석
- LLM으로 map 초안 생성
- LLM으로 SQL 초안 생성 (신규)
  - 전체 대상 또는 특정 shape_name 지정 가능
  - 선택적으로 `sql_hints.json` 파일/추가 힌트 텍스트 입력 가능

## sql_hints.json 예시

`config/sql_hints.sample.json` 참고:

```json
{
  "tbl_pmix_qtr": {
    "business_context": "PMIX SOKBO 분기별 Sales MEQ 보고서",
    "source_table_hint": "mst_psi_simul_report",
    "filters_hint": ["p_module='PMIX'", "s_module='SOKBO'"],
    "notes": ["분기 컬럼 alias는 PPT 헤더와 정확히 맞춰야 함"]
  }
}
```

## SQL 초안 생성 규칙

- bind_type별 전략 기반 SQL 초안 생성
  - text: 단일 값/소수 필드
  - tbl: columns alias 정합
  - tblr: 반복행 placeholder 대응 alias
  - tblx: key_fields + 헤더 alias + CASE WHEN/집계 패턴
  - cht: category_field + series_fields + 정렬
- 생성 후 검증
  - 필수 alias 누락 여부
  - bind_type별 필수 요소 점검
  - SQL 길이/빈값 검사
- 기존 SQL이 있으면 존재 여부/경로/간단 diff를 `.md`에 포함

## 생성 파일

- `output/report_map.generated.json`
- `output/report_map.generated.md`
- `output/sql_drafts/{SQL_KEY}.sql`
- `output/sql_drafts/{SQL_KEY}.md`

## 주의사항

- generated map/SQL은 모두 초안입니다.
- 자동으로 `report_map.json`/`sql/*.sql`을 덮어쓰지 않습니다.
- OpenAI-compatible 호출 실패 시 환경변수/네트워크/응답 형식을 확인하세요.
- map 초안/SQL 초안 생성 모두 동일한 LLM provider 경로(`LLMHelper`)를 사용합니다.

## 다음 7단계 제안

- generated SQL 반영 전 검토/승인 도구
- 실행 실패 원인 LLM 문장형 진단
- map + SQL 동시 초안 생성 wizard
