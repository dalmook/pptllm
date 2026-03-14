"""GUI와 도메인 로직을 연결하는 컨트롤러."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config_loader import ConfigLoader
from app.models import AppPaths, ExecutionSummary
from app.ppt_session import PowerPointSession
from app.sql_loader import SqlLoader
from app.utils.file_helpers import ensure_dir, ensure_file


class AppController:
    """1단계 실행 흐름을 담당한다."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.config_loader = ConfigLoader()
        self.sql_loader = SqlLoader()

    def run(self, paths: AppPaths) -> ExecutionSummary:
        """MVP 실행 플로우를 수행한다."""

        self.logger.info("실행을 시작합니다.")

        self.logger.info("1/5 설정 파일 확인 중...")
        ensure_file(paths.config_file, "설정")

        self.logger.info("2/5 SQL 폴더 확인 및 스캔 중...")
        ensure_dir(paths.sql_dir, "SQL")
        sql_map = self.sql_loader.scan(paths.sql_dir)
        self.logger.info("SQL 파일 %d개를 확인했습니다.", len(sql_map))

        self.logger.info("3/5 PowerPoint 템플릿 확인 중...")
        ensure_file(paths.ppt_template, "PowerPoint 템플릿")

        self.logger.info("4/5 출력 폴더 확인 중...")
        ensure_dir(paths.output_dir, "출력")

        self.logger.info("5/5 설정 로드 및 세션 준비 중...")
        config = self.config_loader.load(paths.config_file)
        ppt_session = PowerPointSession(paths.ppt_template, paths.output_dir)
        ppt_session.validate_paths()

        self.logger.info("보고서명: %s", config.report_name)
        message = ppt_session.run_mock_update()
        self.logger.info(message)
        self.logger.info("실행을 정상 종료했습니다.")

        return ExecutionSummary(
            config_loaded=True,
            sql_files_count=len(sql_map),
            paths_verified=True,
            message=message,
        )

    @staticmethod
    def normalize_paths(
        ppt_path: str,
        config_path: str,
        sql_dir: str,
        output_dir: str,
    ) -> AppPaths:
        """GUI 입력 문자열을 Path 모델로 변환한다."""

        return AppPaths(
            ppt_template=Path(ppt_path).expanduser(),
            config_file=Path(config_path).expanduser(),
            sql_dir=Path(sql_dir).expanduser(),
            output_dir=Path(output_dir).expanduser(),
        )
