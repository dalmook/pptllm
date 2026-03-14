# PPT 보고서 자동화 도구 (1단계 MVP)

기존 PowerPoint VBA 자동화 개념(`text placeholder`, `tbl`, `tblr`, `tblx`)을 유지하면서,
Python + Tkinter 기반 데스크톱 앱으로 점진 이관하기 위한 **실행 가능한 골격 프로젝트**입니다.

> 이번 1단계는 실행 흐름/구조 중심이며, 실제 PPT 바인딩/Oracle 조회는 다음 단계에서 구현합니다.

## 1) 개발 환경 준비 (Windows CMD)

### 가상환경 생성
```cmd
python -m venv .venv
```

### 가상환경 활성화
```cmd
.venv\Scripts\activate
```

### requirements 설치
```cmd
pip install -r requirements.txt
```

## 2) 앱 실행 방법

프로젝트 루트에서 아래 명령 실행:

```cmd
python -m app.main
```

실행 후 GUI에서 다음을 선택합니다.
1. PowerPoint 템플릿 파일 (`.pptx`/`.pptm`)
2. 설정 JSON 파일 (`config/report_map.sample.json` 참고)
3. SQL 폴더
4. Output 폴더

그리고 `실행` 버튼을 누르면 다음 흐름이 로그창에 출력됩니다.
- 설정 파일 확인/로드
- SQL 폴더 스캔
- PPT 파일 경로 확인
- Output 경로 확인
- PPT 바인딩 단계 목업 완료

## 3) PyInstaller 빌드 예시

아래는 단일 실행 파일(onefile) 빌드 예시입니다.

```cmd
pyinstaller --noconfirm --onefile --windowed --name PPTReportTool app\main.py
```

개발 중 디버깅 로그가 필요하면 `--windowed`를 제거한 콘솔 모드도 권장합니다.

```cmd
pyinstaller --noconfirm --onefile --name PPTReportTool app\main.py
```

## 4) 폴더 구조

```text
pptllm/
├─ app/
│  ├─ main.py
│  ├─ gui.py
│  ├─ controller.py
│  ├─ config_loader.py
│  ├─ sql_loader.py
│  ├─ db.py
│  ├─ ppt_session.py
│  ├─ models.py
│  ├─ llm_helper.py
│  ├─ binders/
│  │  ├─ text_binder.py
│  │  ├─ table_binder.py
│  │  ├─ repeat_row_binder.py
│  │  ├─ anchor_fill_binder.py
│  │  └─ chart_binder.py
│  └─ utils/
│     ├─ logger.py
│     ├─ formatters.py
│     └─ file_helpers.py
├─ config/
│  └─ report_map.sample.json
├─ sql/
│  └─ sample.sql
├─ output/
├─ requirements.txt
└─ README.md
```

## 5) 현재 구현 범위 (1단계)

- Tkinter GUI 실행
- 파일/폴더 선택 기능
- 실행 버튼 -> Controller 호출
- 로그창/상태바 표시
- 사용자 친화적 한국어 오류 메시지
- 장기 확장을 위한 모듈 분리 구조
- LLM 연동용 인터페이스(`llm_helper.py`)만 사전 배치

## 6) 향후 확장 계획

1. **실제 Oracle 조회 구현** (`oracledb`)
2. **PowerPoint COM 자동화 구현** (`pywin32`)
3. 기존 VBA 개념을 그대로 매핑하는 Binder 구현
   - `text_binder`: `{{TODAY}}`, `{{SQLKEY__FIELD}}`, `{{SQLKEY__1__FIELD}}`
   - `table_binder`: `tbl`
   - `repeat_row_binder`: `tblr`
   - `anchor_fill_binder`: `tblx`
   - `chart_binder`: 차트 반영
4. 실행 이력/에러 리포트 고도화
5. LLM 보조 기능(설정 추천/검증/요약) 단계적 도입

