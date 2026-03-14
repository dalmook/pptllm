# PPT 보고서 자동화 도구 (4단계: 디버그 리포트 + 구조 분석)

이번 단계는 **실행 실패 원인 추적**과 **PPT 구조 분석 자동화**에 초점을 둡니다.
LLM은 아직 호출하지 않으며, 다음 단계에서 LLM을 쉽게 붙이기 위한 입력 데이터 구조를 준비했습니다.

## 핵심 기능

- 실행 후 디버그 리포트 자동 생성
  - `output/debug_report.json`
  - `output/debug_report.md`
- shape 단위 실행 결과 구조화 수집
  - 상태(success/warning/failed/skipped), row_count, 소요 시간, 메타 정보
- 전역 실행 결과 수집
  - 템플릿/출력/config/sql 경로, SQL row_count, 전체 소요 시간, 예외 정보
- PPT 구조 분석기 추가
  - `output/ppt_structure.json`
  - `output/ppt_structure.md`
- 구조 분석 휴리스틱 기반 추천 bind type 생성
  - `text / tbl / tblr / tblx / cht / none`
- GUI에 `PPT 구조 분석` 버튼 추가
- LLM 인터페이스 준비
  - `build_shape_analysis_payload(...)`
  - `build_map_generation_prompt(...)`
  - `build_sql_generation_prompt(...)`

## Windows CMD 실행

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

## GUI 사용 흐름

1. PowerPoint 템플릿 선택
2. 설정 JSON 선택 (`config/report_map.json`)
3. SQL 폴더 선택
4. Output 폴더 선택
5. `실행` 또는 `PPT 구조 분석` 클릭

## Output 생성 파일

- 실행 시
  - 결과 PPT: `prefix_YYYYMMDD_HHMMSS.pptx`
  - `debug_report.json`
  - `debug_report.md`
- 구조 분석 시
  - `ppt_structure.json`
  - `ppt_structure.md`

## 디버그 리포트 포함 항목

- 실행 시각
- 템플릿 파일 / output 파일 / config 파일 / sql 폴더
- 전체 요약(성공/경고/실패/건너뜀)
- shape별 결과 표
- 실패 목록 / 경고 목록
- SQL row_count 요약
- 성능 요약(총 시간, shape별 시간)
- 예외 발생 시 stack trace

## PPT 구조 분석 리포트 포함 항목

- 분석 시각
- 템플릿 파일
- 슬라이드별 shape 목록
- shape 기본 정보 표
- 표 preview(최대 3행 x 8열)
- placeholder 후보
- anchor token 후보
- 추천 bind type
- 추천 이유

## 바인더 구현 상태

- `text`: 구현
- `tbl`: 구현
- `tblr`: 구현
- `tblx`: 구현
- `cht`: 구현

## 다음 단계(5단계) 연결 포인트

- LLM 기반 report_map 초안 생성기
- shape 분석 결과 -> map JSON 자동 생성
- SQL 초안 생성기
- 오류 원인 문장형 진단

