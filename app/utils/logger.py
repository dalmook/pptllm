"""애플리케이션 로깅 설정."""

from __future__ import annotations

import logging
from logging import Handler


def setup_logger(name: str = "pptllm", level: int = logging.INFO) -> logging.Logger:
    """기본 콘솔 로거를 생성한다."""

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        stream_handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger


def add_handler(logger: logging.Logger, handler: Handler) -> None:
    """GUI 로그 핸들러 등을 추가한다."""

    logger.addHandler(handler)
