#!/usr/bin/env python3
"""
10분마다 교통 소요시간 수집 실행.
로컬 개발: python run_scheduler.py
"""
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

# 프로젝트 루트를 path에 추가
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.collector import run_once

INTERVAL_SEC = 10 * 60  # 10분

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting scheduler: collect every %s minutes", INTERVAL_SEC // 60)
    while True:
        try:
            run_once()
        except Exception as e:
            logger.exception("Collection failed: %s", e)
        logger.info("Next collection in %s minutes", INTERVAL_SEC // 60)
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
