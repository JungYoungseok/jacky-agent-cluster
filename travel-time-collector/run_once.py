#!/usr/bin/env python3
"""
1회 수집 실행. (스케줄러 없이)
사용: python run_once.py   또는  python -m run_once
"""
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

# 프로젝트 루트를 path에 추가
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.collector import run_once

if __name__ == "__main__":
    run_once()
