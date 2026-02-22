"""
카카오모빌리티 길찾기 API (자동차 경로·소요시간)
https://developers.kakaomobility.com/docs/navi-api/directions/
"""
import json
import os
import sys
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

KAKAO_MOBILITY_DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"


def get_car_duration(
    origin_x: float,
    origin_y: float,
    dest_x: float,
    dest_y: float,
    api_key: Optional[str] = None,
) -> Optional[int]:
    """
    출발지→목적지 자동차 소요시간(초) 반환. 실패 시 None.
    """
    key = api_key or os.environ.get("KAKAO_REST_API_KEY")
    if not key:
        logger.warning("KAKAO_REST_API_KEY not set")
        return None

    origin = f"{origin_x},{origin_y}"
    destination = f"{dest_x},{dest_y}"

    params = {
        "origin": origin,
        "destination": destination,
        "summary": "true",
        "priority": "RECOMMEND",
    }
    headers = {
        "Authorization": f"KakaoAK {key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.get(
            KAKAO_MOBILITY_DIRECTIONS_URL,
            params=params,
            headers=headers,
            timeout=15,
        )
        logger.info(
            "Kakao request url=%s status=%s",
            resp.url.split("?")[0],
            resp.status_code,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.exception("Kakao directions request failed: %s", e)
        return None
    except ValueError as e:
        logger.exception("Kakao directions invalid JSON: %s", e)
        return None

    # 응답 결과 로그 (요약)
    routes = data.get("routes") or []
    if not routes:
        logger.warning("Kakao directions: no routes. response keys=%s", list(data.keys()))
        return None

    route = routes[0]
    result_code = route.get("result_code")
    result_msg = route.get("result_msg", "")
    summary = route.get("summary") or {}
    duration_sec = summary.get("duration")
    distance_m = summary.get("distance")

    logger.info(
        "Kakao API response result: result_code=%s result_msg=%s duration_sec=%s distance_m=%s",
        result_code,
        result_msg,
        duration_sec,
        distance_m,
    )
    if os.environ.get("KAKAO_DEBUG", "").strip() in ("1", "true", "yes"):
        safe_data = {"routes": [{"result_code": r.get("result_code"), "result_msg": r.get("result_msg"), "summary": r.get("summary")} for r in data.get("routes", [])]}
        print("[Kakao response body]", file=sys.stderr, flush=True)
        print(json.dumps(safe_data, ensure_ascii=False, indent=2), file=sys.stderr, flush=True)

    if result_code != 0:
        logger.warning("Kakao directions result: %s", result_msg)
        return None

    if duration_sec is not None:
        return int(duration_sec)
    return None
