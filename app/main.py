"""애플리케이션 엔트리포인트."""

from __future__ import annotations

from app.controller import AppController
from app.gui import ReportAutomationApp
from app.utils.logger import setup_logger


def main() -> None:
    """앱을 초기화하고 Tkinter 메인 루프를 실행한다."""

    logger = setup_logger()
    controller = AppController(logger=logger)
    app = ReportAutomationApp(controller=controller, logger=logger)
    app.mainloop()


if __name__ == "__main__":
    main()
