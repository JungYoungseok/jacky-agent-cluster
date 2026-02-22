"""
빗썸금융타워 → 주요 거점 자동차/대중교통 소요시간 수집.
수집 결과는 Datadog 연동을 위해 JSON 로그로 출력.
"""
import json
import logging
import math
import sys
from datetime import datetime, timezone

from config.locations import ORIGIN, DESTINATIONS
from src.kakao_client import get_car_duration
from src.odsay_client import get_transit_duration

# JSON 한 줄 로그용 (Datadog / CloudWatch Logs 수집에 적합)
logger = logging.getLogger(__name__)


def collect_one_route(origin: dict, dest: dict) -> dict:
    """한 개 목적지에 대해 자동차·대중교통 소요시간 수집."""
    ox, oy = origin["x"], origin["y"]
    dx, dy = dest["x"], dest["y"]

    car_sec = get_car_duration(ox, oy, dx, dy)
    transit_sec = get_transit_duration(ox, oy, dx, dy)

    # 분 단위는 올림(ceil)으로 표시 (초는 그대로 유지)
    return {
        "destination": dest["name"],
        "car_duration_sec": car_sec,
        "transit_duration_sec": transit_sec,
        "car_duration_min": math.ceil(car_sec / 60) if car_sec is not None else None,
        "transit_duration_min": math.ceil(transit_sec / 60) if transit_sec is not None else None,
    }


def collect_all() -> list[dict]:
    """출발지 1곳, 목적지 N곳 전체 수집."""
    results = []
    for dest in DESTINATIONS:
        row = collect_one_route(ORIGIN, dest)
        results.append(row)
    return results


def emit_log_payload(records: list[dict]) -> None:
    """
    Datadog에서 파싱·대시보드용으로 사용할 수 있도록
    한 줄 JSON 로그로 stdout에 출력.
    """
    payload = {
        "service": "travel-time-collector",
        "collect_time_iso": datetime.now(timezone.utc).isoformat(),
        "origin": ORIGIN["name"],
        "routes": records,
    }
    # 한 줄 JSON (로그 수집기 파싱에 유리)
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def run_once() -> None:
    """1회 수집 후 JSON 로그 출력."""
    logger.info("Collecting travel times: %s -> %s", ORIGIN["name"], [d["name"] for d in DESTINATIONS])
    records = collect_all()
    emit_log_payload(records)
    logger.info("Collected %d routes", len(records))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    run_once()
