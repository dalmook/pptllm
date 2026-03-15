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

## LLM Provider 설정 (Windows CMD 상세)

기본값은 `mock`입니다. 즉, 아무 설정 없이 실행하면 실제 LLM 호출 없이 휴리스틱 초안만 생성합니다.

### 1) Mock → 실제 LLM으로 바꾸는 핵심

아래 1줄이 가장 중요합니다.

```cmd
set LLM_PROVIDER=openai_compatible
```

또는 GPT-OSS를 쓸 경우:

```cmd
set LLM_PROVIDER=gpt_oss
```

`LLM_PROVIDER=mock` 상태면 API 키를 넣어도 외부 LLM을 호출하지 않습니다.

### 2) OpenAI-compatible provider 설정

```cmd
set LLM_PROVIDER=openai_compatible
set LLM_BASE_URL=https://api.openai.com/v1
set LLM_MODEL=gpt-4o-mini
set LLM_API_KEY=YOUR_API_KEY
set LLM_API_STYLE=auto
```

- `LLM_API_STYLE`
  - `auto`(권장): `responses` 먼저 시도 후 실패하면 `chat.completions` fallback
  - `responses`: Responses API만 사용
  - `chat`: Chat Completions API만 사용

### 3) GPT-OSS gateway provider 설정

```cmd
set LLM_PROVIDER=gpt_oss
set GPT_OSS_API_URL=http://apigw.samsungds.net:8000/gpt-oss/1/gpt-oss-120b/v1/chat/completions
set GPT_OSS_CREDENTIAL_KEY=credential:...
set GPT_OSS_USER_ID=your.adid
set GPT_OSS_USER_TYPE=AD_ID
set GPT_OSS_SEND_SYSTEM_NAME=GOC_MAIL_RAG_PIPELINE
set GPT_OSS_MODEL=openai/gpt-oss-120b
```

이 모드는 제공해주신 `gpt_oss_example.py`와 동일하게 아래 헤더를 포함해 호출합니다.
- `x-dep-ticket`
- `Send-System-Name`
- `User-Id`
- `User-Type`
- `Prompt-Msg-Id`
- `Completion-Msg-Id`

### 4) CMD에서 즉시 적용 vs 영구 적용

- 현재 CMD 창에서만 적용: `set KEY=value`
- 새 CMD에도 유지(영구): `setx KEY "value"`

예시:

```cmd
setx LLM_PROVIDER "openai_compatible"
setx LLM_BASE_URL "https://api.openai.com/v1"
setx LLM_MODEL "gpt-4o-mini"
setx LLM_API_KEY "YOUR_API_KEY"
```

> `setx`는 **새로 연 CMD 창**부터 반영됩니다.

### 5) 설정 확인 방법

```cmd
echo %LLM_PROVIDER%
echo %LLM_BASE_URL%
echo %LLM_MODEL%
```

### 6) 자주 하는 실수 체크리스트

- `%LLM_PROVIDER%`가 여전히 `mock`인지 확인
- API Key 누락/오타 확인
- 사내망/프록시 환경에서 `LLM_BASE_URL` 접근 가능 여부 확인
- GPT-OSS 사용 시 `GPT_OSS_CREDENTIAL_KEY` 만료 여부 확인

`.env.example` 참고.



## Windows CMD 실행 (처음부터 순서대로)

```cmd
cd /d C:\path\to\pptllm
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

1. 먼저 LLM provider를 선택합니다.
   - 빠른 테스트: `set LLM_PROVIDER=mock`
   - 실제 LLM: 위 "LLM Provider 설정" 섹션대로 환경변수 설정
2. Oracle DB 사용 시 "Oracle 연결 설정"도 함께 설정합니다.
3. 앱 실행:

```cmd
python -m app.main
```

4. GUI에서 순서 권장:
   - `PPT 구조 분석`
   - `LLM으로 map 초안 생성`
   - `LLM으로 SQL 초안 생성`
   - (검토 후) `실행`

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
