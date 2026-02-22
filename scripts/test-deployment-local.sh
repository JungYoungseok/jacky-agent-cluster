#!/usr/bin/env bash
# Deployment 동작( run_hourly.py ) 로컬 검증. 프로젝트 루트에서 실행.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COLLECTOR_DIR="$ROOT_DIR/travel-time-collector"

echo "=== 1) Python으로 run_hourly 동작 확인 ==="
echo "RUN_FIRST_IMMEDIATELY=1 이면 곧바로 run_once 1회 실행 후 다음 정각까지 대기합니다."
echo "stdout에 JSON 한 줄이 나오면 성공. 확인 후 Ctrl+C로 종료하세요."
echo ""

cd "$COLLECTOR_DIR"
if [[ -n "$SKIP_PYTHON" ]]; then
  echo "SKIP_PYTHON set, skipping."
else
  RUN_FIRST_IMMEDIATELY=1 python run_hourly.py
fi

echo ""
echo "=== 2) Docker로 확인 (선택) ==="
echo "  cd $COLLECTOR_DIR && docker build -t travel-time-collector:latest ."
echo "  docker run --rm --env-file .env -e RUN_FIRST_IMMEDIATELY=1 travel-time-collector:latest"
