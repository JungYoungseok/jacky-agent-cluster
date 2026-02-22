# 교통 소요시간 수집 서비스 개발 안내

빗썸금융타워를 출발지로, 판교역·광화문역·삼성전자 수원사업장·LG사이언스파크 마곡까지 **자동차**와 **대중교통** 소요시간을 **10분마다** 수집해 로그로 남기는 서비스입니다.  
로그는 이후 Datadog으로 전송해 대시보드에 표시할 예정입니다.

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| 출발지 | 빗썸금융타워 (강남N타워, 테헤란로 129) |
| 목적지 | 판교역, 광화문역, 삼성전자 수원사업장, LG사이언스파크 마곡 |
| 수집 주기 | 10분 |
| 자동차 소요시간 | **Kakao** 카카오모빌리티 길찾기 API |
| 대중교통 소요시간 | **ODsay** 대중교통 길찾기 API (카카오는 대중교통 미제공) |
| 출력 | JSON 한 줄 로그 (stdout) → Datadog 수집용 |

---

## 2. 로컬 개발 환경 준비

### 2.1 Python 및 패키지

- Python 3.10 이상
- 프로젝트 디렉터리: `travel-time-collector/`

```bash
cd travel-time-collector
pip install -r requirements.txt
```

### 2.2 API 키 발급

**자동차 (필수)**

1. [카카오 개발자 콘솔](https://developers.kakao.com/) 접속
2. 앱 생성 후 **카카오모빌리티** 서비스 활성화
3. [카카오모빌리티 디벨로퍼스](https://developers.kakaomobility.com/)에서 동일 앱의 REST API 키 확인 (또는 카카오 앱 REST API 키 사용)
4. 환경 변수 `KAKAO_REST_API_KEY`에 저장

**대중교통 (선택)**

1. [ODsay LAB](https://lab.odsay.com/) 회원가입
2. 대중교통 길찾기 API 키 발급
3. 환경 변수 `ODSAY_API_KEY`에 저장  
   - 없으면 대중교통은 수집하지 않고, 자동차만 수집됨

### 2.3 환경 변수 설정

```bash
# 방법 1: .env 파일 (프로젝트 루트 travel-time-collector/.env)
cp .env.example .env
# .env 편집 후 KAKAO_REST_API_KEY, ODSAY_API_KEY 입력

# 방법 2: 셸에서 직접
export KAKAO_REST_API_KEY=your_kakao_rest_api_key
export ODSAY_API_KEY=your_odsay_api_key
```

`run_once.py`, `run_scheduler.py` 실행 시 `.env`를 자동으로 로드합니다.

---

## 3. 실행 방법

### 3.1 1회만 수집 (테스트용)

```bash
cd travel-time-collector
python run_once.py
```

- **stdout**: JSON 한 줄 (수집 결과)
- **stderr**: INFO 등 일반 로그

### 3.2 10분마다 수집 (스케줄러)

```bash
cd travel-time-collector
python run_scheduler.py
```

- 10분 간격으로 `run_once()` 호출
- 중간에 예외가 나도 로그 남긴 뒤 다음 주기까지 대기

---

## 4. 출력 로그 형식 (Datadog 연동용)

stdout에 출력되는 한 줄 JSON 예시:

```json
{
  "service": "travel-time-collector",
  "collect_time_iso": "2025-02-22T12:00:00.123456+00:00",
  "origin": "빗썸금융타워",
  "routes": [
    {
      "destination": "판교역",
      "car_duration_sec": 1842,
      "transit_duration_sec": 2580,
      "car_duration_min": 30.7,
      "transit_duration_min": 43.0
    },
    ...
  ]
}
```

| 필드 | 설명 |
|------|------|
| `service` | 서비스 식별자 (Datadog 서비스명으로 사용 가능) |
| `collect_time_iso` | 수집 시각 (UTC ISO 8601) |
| `origin` | 출발지 이름 |
| `routes` | 목적지별 소요시간 배열 |
| `destination` | 목적지 이름 |
| `car_duration_sec` / `transit_duration_sec` | 자동차/대중교통 소요시간(초), 실패 시 `null` |
| `car_duration_min` / `transit_duration_min` | 분 단위(소수), 실패 시 `null` |

Datadog에서는 이 JSON을 파싱해 `routes` 배열의 `destination`, `car_duration_sec`, `transit_duration_sec` 등으로 시계열/테이블 위젯을 만들 수 있습니다.

---

## 5. 프로젝트 구조

```
travel-time-collector/
├── config/
│   └── locations.py    # 출발지·목적지 좌표 (빗썸금융타워, 판교역 등)
├── src/
│   ├── kakao_client.py # 카카오모빌리티 자동차 길찾기
│   ├── odsay_client.py # ODsay 대중교통 길찾기
│   └── collector.py    # 수집 로직 + JSON 로그 출력
├── run_once.py         # 1회 수집
├── run_scheduler.py    # 10분 스케줄
├── requirements.txt
├── .env.example
└── README.md
```

- **좌표 변경**: `config/locations.py`에서 `ORIGIN`, `DESTINATIONS` 수정
- **수집 주기 변경**: `run_scheduler.py`의 `INTERVAL_SEC` (기본 600 = 10분)

---

## 6. 다음 단계 (EKS + Datadog)

1. **EKS 배포**: 이 서비스를 컨테이너 이미지로 빌드해 CronJob 또는 Deployment로 배포
2. **Datadog Agent**: Pod 로그 수집 시 stdout JSON만 수집하도록 설정
3. **Datadog 로그 파이프라인**: `service:travel-time-collector` JSON 파싱 규칙 추가
4. **대시보드**: 파싱된 `car_duration_sec`, `transit_duration_sec`, `destination` 기준 시계열/쿼리 위젯 구성

상세한 EKS 배포·Datadog 연동 절차는 별도 가이드에서 다룹니다.
