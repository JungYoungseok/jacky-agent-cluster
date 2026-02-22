#!/usr/bin/env python3
"""
매 시간 정각(한국 시간 0분)에 run_once 실행.
Deployment에서 사용.
"""
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo
else:
    ZoneInfo = None  # type: ignore

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

TZ = "Asia/Seoul"


def next_run_at_kst():
    if ZoneInfo:
        tz = ZoneInfo(TZ)
        now = datetime.now(tz)
    else:
        now = datetime.utcnow()
        now = now.replace(tzinfo=None) + timedelta(hours=9)
    # 다음 정각(0분)
    next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return next_run, now


def sleep_until(next_run, now):
    delta = (next_run - now).total_seconds()
    if delta > 0:
        logger.info("Next run at %s (KST), sleeping %.0f s", next_run, delta)
        time.sleep(delta)


def main():
    import os
    # Docker 등에서 출력이 안 보일 수 있으므로 시작 메시지를 stdout으로 즉시 출력
    run_first_immediately = os.environ.get("RUN_FIRST_IMMEDIATELY", "").strip().lower() in ("1", "true", "yes")
    print("travel-time-collector hourly started (KST %s)%s" % (TZ, ", first run immediately" if run_first_immediately else ""), flush=True)
    logger.info("Hourly collector started (KST %s)%s", TZ, ", first run immediately (local test)" if run_first_immediately else "")
    from src.collector import run_once
    while True:
        next_run, now = next_run_at_kst()
        if not run_first_immediately:
            sleep_until(next_run, now)
        else:
            run_first_immediately = False  # 다음 루프부터는 정각 대기
        try:
            run_once()
        except Exception as e:
            logger.exception("Hourly run failed: %s", e)
        time.sleep(60)


if __name__ == "__main__":
    main()
