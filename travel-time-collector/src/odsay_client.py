"""
ODsay 대중교통 경로 API (지하철/버스 소요시간)
https://lab.odsay.com/ 에서 API 키 발급
카카오는 대중교통 길찾기 API를 제공하지 않아 ODsay 사용.
- info.totalWalk: 마지막 정류장→목적지 도보 거리(m)
- info.totalWalkTime: 총 도보 시간(분), -1이면 미제공일 수 있음
"""
import json
import math
import os
import sys
import logging
from typing import Optional

import requests

# 위경도 거리(m), Haversine 근사
def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))

logger = logging.getLogger(__name__)

ODSAY_PUB_TRANS_URL = "https://api.odsay.com/v1/api/searchPubTransPathT"


def get_transit_duration(
    origin_x: float,
    origin_y: float,
    dest_x: float,
    dest_y: float,
    api_key: Optional[str] = None,
) -> Optional[int]:
    """
    출발지→목적지 대중교통 소요시간(초) 반환. 실패 시 None.
    ODsay는 경도(SX, EX), 위도(SY, EY) 순서.
    """
    key = api_key or os.environ.get("ODSAY_API_KEY")
    if not key:
        logger.warning("ODSAY_API_KEY not set; transit duration will be skipped")
        return None

    params = {
        "apiKey": key,
        "SX": origin_x,
        "SY": origin_y,
        "EX": dest_x,
        "EY": dest_y,
        "OPT": 0,
        "resultType": "json",
    }

    try:
        resp = requests.get(
            ODSAY_PUB_TRANS_URL,
            params=params,
            timeout=15,
        )
        # Output log: 요청 결과
        logger.info(
            "ODsay request url=%s status=%s",
            resp.url.split("?")[0],
            resp.status_code,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.exception("ODsay transit request failed: %s", e)
        return None
    except ValueError as e:
        logger.exception("ODsay transit invalid JSON: %s", e)
        return None

    result = data.get("result")
    result_code = result.get("code") if isinstance(result, dict) else None
    result_msg = result.get("message", "unknown") if isinstance(result, dict) else "unknown"
    path_list_for_log = result.get("path") or [] if isinstance(result, dict) else []
    path_count = len(path_list_for_log)
    first_path = path_list_for_log[0] if path_list_for_log else {}
    info = first_path.get("info") or first_path if isinstance(first_path, dict) else {}
    total_time = info.get("totalTime") if isinstance(info, dict) else None
    payment = info.get("payment") if isinstance(info, dict) else None
    subway_count = info.get("subwayTransitCount") if isinstance(info, dict) else None
    bus_count = info.get("busTransitCount") if isinstance(info, dict) else None
    first_station = info.get("firstStartStation") if isinstance(info, dict) else None
    last_station = info.get("lastEndStation") if isinstance(info, dict) else None
    total_walk_m = info.get("totalWalk") if isinstance(info, dict) else None  # 총 도보 거리(m), 마지막 역~목적지 포함
    total_walk_time_info = info.get("totalWalkTime") if isinstance(info, dict) else None  # 총 도보 시간(분), -1이면 미제공

    logger.info(
        "ODsay API response result: result.code=%s path_count=%s totalTime_min=%s payment=%s subwayTransitCount=%s busTransitCount=%s firstStartStation=%s lastEndStation=%s totalWalk_m=%s totalWalkTime_min=%s",
        result_code,
        path_count,
        total_time,
        payment,
        subway_count,
        bus_count,
        first_station,
        last_station,
        total_walk_m,
        total_walk_time_info,
    )
    # 환경변수 ODSAY_DEBUG=1 일 때만 응답 본문 출력 (디버깅용)
    if os.environ.get("ODSAY_DEBUG", "").strip() in ("1", "true", "yes"):
        safe_data = {k: v for k, v in data.items() if k != "apiKey"}
        body_full = json.dumps(safe_data, ensure_ascii=False, indent=2)
        print("[ODsay response body]", file=sys.stderr, flush=True)
        print(body_full, file=sys.stderr, flush=True)

    # ODsay는 성공 시 result에 code 필드가 없을 수 있음. path가 있으면 성공으로 처리
    if isinstance(result, dict) and result.get("code") is not None and str(result.get("code")) != "0":
        logger.warning("ODsay result not success: code=%s message=%s", result_code, result_msg)
        return None

    # ODsay 실제 응답 구조에 맞춰 path 추출 (result.path 또는 result.subPath 등)
    path_list = []
    if isinstance(result, dict):
        path_list = result.get("path") or result.get("subPath") or []
    if not path_list:
        logger.warning("ODsay: no path in result (result keys: %s)", list(result.keys()) if isinstance(result, dict) else "n/a")
        return None

    first_path = path_list[0] if isinstance(path_list[0], dict) else {}
    info = first_path.get("info") or first_path
    sub_paths = first_path.get("subPath") or []

    # subPath에서 도보 구간( trafficType 3=도보 )만 합산 → 로그로 확인용
    walk_section_min = 0
    for s in sub_paths:
        if isinstance(s, dict) and s.get("trafficType") == 3:
            walk_section_min += int(s.get("sectionTime", 0))
    total_walk_m = info.get("totalWalk") if isinstance(info, dict) else None
    total_walk_time = info.get("totalWalkTime") if isinstance(info, dict) else None

    # 출발지~첫 역 도보: subPath 첫 구간이 도보면 sectionTime, distance 로그
    first_seg = sub_paths[0] if sub_paths and isinstance(sub_paths[0], dict) else {}
    last_walk_seg = None
    for s in reversed(sub_paths):
        if isinstance(s, dict) and s.get("trafficType") == 3:
            last_walk_seg = s
            break
    first_walk_min = int(first_seg.get("sectionTime", 0)) if first_seg.get("trafficType") == 3 else 0
    first_walk_m = int(first_seg.get("distance", 0)) if first_seg.get("trafficType") == 3 else 0
    last_walk_min = int(last_walk_seg.get("sectionTime", 0)) if last_walk_seg else 0
    last_walk_m = int(last_walk_seg.get("distance", 0)) if last_walk_seg else 0
    logger.info(
        "ODsay 도보: 출발지~첫역 sectionTime=%s min distance=%s m | 마지막역~목적지 sectionTime=%s min distance=%s m | totalWalk_m=%s totalWalkTime_min=%s subPath 도보합=%s min",
        first_walk_min,
        first_walk_m,
        last_walk_min,
        last_walk_m,
        total_walk_m,
        total_walk_time,
        walk_section_min,
    )

    # ODsay 문서: info.totalTime = 도보 + 전철/버스 이동 + 환승 대기 포함한 총 소요시간(분)
    total_time_min: Optional[float] = None
    total_time = info.get("totalTime") if isinstance(info, dict) else None

    if total_time is not None and int(total_time) > 0:
        total_time_min = float(int(total_time))
        logger.info(
            "ODsay totalTime=%s min -> %s sec (도보·전철·환승대기 포함, totalWalkTime=%s)",
            total_time_min,
            int(total_time_min * 60),
            total_walk_time,
        )
        # [보정1] 출발지~첫 역 도보: ODsay가 과소 추정하는 경우 보정
        # (1) 환경변수 ODSAY_FIRST_WALK_MIN=N 사용 시: 실제 출발지~첫 역이 N분 걸리면 N분 미만일 때 부족분 추가
        # (2) 미설정 시: 첫 역 좌표로 직선거리 계산 후 80m/분 추정 (직선이라 실제 도보보다 짧게 나올 수 있음)
        add_first = 0
        first_walk_min_env = os.environ.get("ODSAY_FIRST_WALK_MIN", "").strip()
        if first_walk_min_env and first_walk_min_env.isdigit():
            min_first_walk = int(first_walk_min_env)
            if min_first_walk > first_walk_min:
                add_first = min_first_walk - first_walk_min
                logger.info(
                    "ODsay 보정: 출발지~첫 역 도보 %s분 추가 (ODSAY_FIRST_WALK_MIN=%s, ODsay %s분) -> 총 %s min",
                    add_first,
                    min_first_walk,
                    first_walk_min,
                    total_time_min + add_first,
                )
        if add_first == 0:
            first_station_x = first_station_y = None
            for s in sub_paths:
                if isinstance(s, dict) and s.get("trafficType") == 1:
                    first_station_x = s.get("startX")
                    first_station_y = s.get("startY")
                    break
            if first_station_x is not None and first_station_y is not None:
                dist_m = _haversine_m(origin_x, origin_y, float(first_station_x), float(first_station_y))
                est_first_walk = math.ceil(dist_m / 80.0)
                if est_first_walk > first_walk_min:
                    add_first = est_first_walk - first_walk_min
                    logger.info(
                        "ODsay 보정: 출발지~첫 역 도보 %s분 추가 (직선 %.0fm, 추정 %s분, ODsay %s분) -> 총 %s min",
                        add_first,
                        dist_m,
                        est_first_walk,
                        first_walk_min,
                        total_time_min + add_first,
                    )
            elif first_walk_m > 0:
                est_first_walk = math.ceil(first_walk_m / 80.0)
                if est_first_walk > first_walk_min:
                    add_first = est_first_walk - first_walk_min
                    logger.info(
                        "ODsay 보정: 출발지~첫 역 도보 %s분 추가 (거리 %sm, ODsay %s분 -> 추정 %s분) -> 총 %s min",
                        add_first,
                        first_walk_m,
                        first_walk_min,
                        est_first_walk,
                        total_time_min + add_first,
                    )
        if add_first > 0:
            total_time_min += add_first
        # [보정2] totalWalkTime이 -1(미제공)이고 totalWalk(도보 거리)가 크면, 마지막 역~목적지 도보가 과소 반영됐을 수 있음 → 추정분 추가
        walk_m = int(total_walk_m) if total_walk_m is not None else 0
        if total_walk_time in (-1, None) and walk_m > 500:
            # 도보 약 80m/분 가정, 올림
            add_walk_min = math.ceil(walk_m / 80.0)
            total_time_min += add_walk_min
            logger.info(
                "ODsay 보정: 마지막 역~목적지 도보 추정 %s분 추가 (totalWalk=%sm, totalWalkTime 미제공) -> 총 %s min",
                add_walk_min,
                walk_m,
                total_time_min,
            )

    # totalTime 없을 때만 subPath sectionTime 합 사용 (환승대기 미포함)
    if total_time_min is None or total_time_min <= 0:
        if sub_paths:
            sum_section_min = sum(
                int(s.get("sectionTime", 0)) for s in sub_paths if isinstance(s, dict)
            )
            if sum_section_min > 0:
                total_time_min = float(sum_section_min)
                logger.info(
                    "ODsay fallback: subPath sectionTimes sum=%s min (환승대기 미포함 가능)",
                    total_time_min,
                )

    if total_time_min is None or total_time_min <= 0:
        logger.warning("ODsay: could not compute total time. first_path keys: %s", list(first_path.keys()))
        return None

    total_time_sec = int(total_time_min * 60)
    return total_time_sec
