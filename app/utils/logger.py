"""애플리케이션 로깅 설정."""

from __future__ import annotations

import logging


def setup_logger(name: str = "pptllm", level: int = logging.DEBUG) -> logging.Logger:
    """콘솔 + GUI에서 재사용할 표준 로거를 생성한다."""

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger
