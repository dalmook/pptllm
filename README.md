# PPT 보고서 자동화 도구 (2단계: 실행 엔진 v1)

기존 VBA 개념(placeholder / `tbl` / `tblr` / `tblx` / chart)을 Python 구조로 옮기는 프로젝트입니다.
이번 단계에서는 **실제로 동작하는 엔진 v1**을 붙였고, 우선순위 기능인 **text + tbl 바인더**를 구현했습니다.

## 이번 단계 구현 범위

- Tkinter GUI에서 경로 선택 및 실행
- `config/report_map.json` 로드 및 검증
- `sql/*.sql` 자동 스캔 (utf-8 우선, cp949 fallback)
- Oracle DB 실제 조회 (`oracledb`)
- PowerPoint COM 열기/바인딩/결과 SaveAs (`pywin32`)
- 실제 구현
  - `text` binder: `{{TODAY}}`, `{{SQLKEY__FIELD}}`, `{{SQLKEY__1__FIELD}}`
  - `tbl` binder: columns/header_row/clear_existing 반영
- 스켈레톤(부분 구현)
  - `tblr`, `tblx`, `cht`

## 1) 개발 환경 준비 (Windows CMD)

### 가상환경 생성
```cmd
python -m venv .venv
```

### 가상환경 활성화
```cmd
.venv\Scripts\activate
```

### 패키지 설치
```cmd
pip install -r requirements.txt
```

## 2) 실행 방법

```cmd
python -m app.main
```

GUI에서 아래를 선택한 뒤 `실행` 버튼을 누릅니다.
1. PowerPoint 템플릿 (`.pptx`/`.pptm`)
2. config 파일 (`config/report_map.json`)
3. SQL 폴더 (`sql`)
4. output 폴더 (`output`)

성공 시 output 폴더에 `output_filename_prefix_YYYYMMDD_HHMMSS.pptx` 형태로 저장됩니다.

## 3) report_map.json 구조

`shape_name` 기준으로 바인딩 정보를 정의합니다.

```json
{
  "report_name": "주간 실적 보고서",
  "output_filename_prefix": "weekly_report",
  "db": {
    "user": "SCOTT",
    "password": "TIGER",
    "dsn": "127.0.0.1:1521/ORCLPDB1"
  },
  "bindings": [
    {
      "shape_name": "txt_title",
      "bind_type": "text",
      "enabled": true
    },
    {
      "shape_name": "tbl_sales",
      "bind_type": "tbl",
      "sql_key": "sales_table",
      "columns": ["DIVISION", "SALES", "GROWTH"],
      "header_row": 1,
      "clear_existing": true,
      "enabled": true
    }
  ]
}
```

주요 필드:
- 공통: `shape_name`, `bind_type`, `sql_key`, `enabled`
- tbl: `columns`, `header_row`, `clear_existing`
- tblr: `template_row` (이번 단계 스켈레톤)
- tblx: `key_fields` (이번 단계 스켈레톤)
- cht: `category_field`, `series_fields` (이번 단계 스켈레톤)

## 4) SQL 파일 규칙

- 파일명(확장자 제외)이 `SQL_KEY`입니다.
- 예: `sql/sales_table.sql` -> `sql_key = "sales_table"`
- 인코딩은 utf-8 우선, 실패 시 cp949로 재시도
- 빈 SQL 파일은 경고 로그 후 스킵

## 5) PyInstaller 예시

```cmd
pyinstaller --noconfirm --onefile --windowed --name PPTReportTool app\main.py
```

## 6) 현재 제한 사항

- `tblr` / `tblx` / `cht`는 인터페이스와 흐름만 준비된 상태입니다.
- Linux/macOS에서는 COM 자동화가 동작하지 않으므로 Windows에서 테스트해야 합니다.
- LLM 기능은 아직 미구현(의도된 상태)입니다.

## 7) 폴더 구조

```text
pptllm/
├─ app/
│  ├─ binders/
│  ├─ config_loader.py
│  ├─ controller.py
│  ├─ db.py
│  ├─ gui.py
│  ├─ llm_helper.py
│  ├─ main.py
│  ├─ models.py
│  ├─ ppt_session.py
│  ├─ sql_loader.py
│  └─ utils/
├─ config/
│  ├─ report_map.json
│  └─ report_map.sample.json
├─ sql/
├─ output/
├─ requirements.txt
└─ README.md
```
