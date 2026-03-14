# PPT 보고서 자동화 도구 (3단계: 바인딩 엔진 확장)

기존 VBA 개념(placeholder / `tbl` / `tblr` / `tblx` / `cht`)을 Python + Tkinter + pywin32 + oracledb 구조로 옮긴 프로젝트입니다.
이번 3단계에서는 실무형으로 **`tblr` / `tblx` / `cht`를 실제 동작 구현**했습니다.

## 1) 이번 단계 구현 범위

- GUI 실행/로그/상태 표시
- `report_map.json` 로드 및 bind_type별 검증 강화
- SQL 파일 자동 스캔 (utf-8 우선, cp949 fallback)
- Oracle DB 조회 실행
- PowerPoint COM 자동화 열기/저장/shape 탐색
- 실제 바인더 구현
  - `text`: `{{TODAY}}`, `{{SQLKEY__FIELD}}`, `{{SQLKEY__1__FIELD}}`
  - `tbl`: 정형표 채움
  - `tblr`: template_row 반복행 채움 + 빈 결과 옵션
  - `tblx`: anchor token(`{{A|B|C}}`) + key_fields 매칭 + 우측 채움
  - `cht`: category/series 기반 차트 데이터 갱신

## 2) 개발 환경 준비 (Windows CMD)

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 3) 실행 방법

```cmd
python -m app.main
```

GUI에서 아래를 선택 후 실행합니다.
1. PowerPoint 템플릿 (`.pptx`/`.pptm`)
2. 설정 JSON (`config/report_map.json`)
3. SQL 폴더 (`sql`)
4. output 폴더 (`output`)

성공 시 output 폴더에 `prefix_YYYYMMDD_HHMMSS.pptx`가 생성됩니다.

## 4) report_map.json 구조

핵심 옵션:
- 공통: `shape_name`, `bind_type`, `sql_key`, `enabled`, `clear_existing`
- tblr: `template_row`, `keep_template_row_if_empty`, `clear_placeholders_if_empty`
- tblx: `header_row`, `key_fields`, `strict_match`
- cht: `category_field`, `series_fields`

### 샘플

```json
{
  "bindings": [
    {
      "shape_name": "tbl_sales_main",
      "bind_type": "tbl",
      "sql_key": "SALES_MAIN",
      "columns": ["MONTH", "DD", "ITEM", "QTY", "AMT"],
      "header_row": 1,
      "clear_existing": true,
      "enabled": true
    },
    {
      "shape_name": "tbl_sales_repeat",
      "bind_type": "tblr",
      "sql_key": "SALES_DAILY",
      "template_row": 5,
      "enabled": true,
      "keep_template_row_if_empty": true,
      "clear_placeholders_if_empty": true
    },
    {
      "shape_name": "tbl_pmix_qtr",
      "bind_type": "tblx",
      "sql_key": "PMIX_QTR",
      "header_row": 1,
      "key_fields": ["FAM1", "USERFAM1", "DR"],
      "enabled": true,
      "strict_match": false
    },
    {
      "shape_name": "cht_sales_trend",
      "bind_type": "cht",
      "sql_key": "SALES_TREND",
      "category_field": "MONTH",
      "series_fields": ["QTY", "AMT"],
      "enabled": true
    }
  ]
}
```

## 5) bind_type 사용 예시

### 5-1) tblr
- 템플릿 행 셀 예시: `{{ROWNUM}}`, `{{FIELD}}`, `{{TODAY}}`
- 결과가 0건일 때
  - `keep_template_row_if_empty=true`: 템플릿 행 유지
  - `clear_placeholders_if_empty=true`: placeholder만 공백 치환

### 5-2) tblx
- 앵커 셀 예시: `{{DRAM|C.DRAM|D1A}}`
- `key_fields=["FAM1","USERFAM1","DR"]`와 토큰 매칭
- 매칭된 1행의 컬럼 값을 헤더명 기준으로 우측 채움

### 5-3) cht
- `category_field`를 X축으로 사용
- `series_fields`는 시리즈 값으로 사용
- 기존 차트 서식은 유지하고 데이터만 교체 시도

## 6) SQL 파일 규칙

- 파일명(확장자 제외)이 SQL_KEY
- 예: `sql/sales_table.sql` -> `sales_table`
- utf-8 우선, 실패 시 cp949 재시도
- 빈 SQL 파일은 경고 로그 출력

## 7) 테스트 방법

### 정적 점검
```cmd
python -m compileall app config
```

### 로더 스모크 테스트
```cmd
python -c "from pathlib import Path; from app.config_loader import ConfigLoader; print(ConfigLoader().load(Path('config/report_map.json')).report_name)"
```

> Oracle/PowerPoint COM 런타임 테스트는 Windows + Office + Oracle 접근 환경에서 수행하세요.

## 8) PyInstaller 예시

```cmd
pyinstaller --noconfirm --onefile --windowed --name PPTReportTool app\main.py
```

## 9) 현재 한계

- 차트 데이터시트 갱신은 일반 차트 유형 기준으로 구현됨
- 병합 셀/복잡한 표 구조는 `tblr`에서 경고 로그 후 진행
- COM 객체 특성상 환경별 동작 차이가 있을 수 있음

