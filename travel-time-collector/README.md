# 교통 소요시간 수집 서비스 (Travel Time Collector)

빗썸금융타워를 **출발지**로, 아래 **목적지**까지 **자동차**·**대중교통** 소요시간을 10분마다 수집해 JSON 로그로 남깁니다.  
이 로그는 이후 Datadog으로 전송해 대시보드에 표시할 수 있습니다.

## 목적지

| 목적지 |
|--------|
| 판교역 |
| 광화문역 |
| 삼성전자 수원사업장 |
| LG사이언스파크 마곡 |

## API 사용

- **자동차 소요시간**: [카카오모빌리티 길찾기 API](https://developers.kakaomobility.com/docs/navi-api/directions/) (Kakao)
- **대중교통 소요시간**: [ODsay 대중교통 길찾기 API](https://lab.odsay.com/)  
  (카카오는 대중교통 경로 API를 제공하지 않아 ODsay 사용)

## 로컬 개발 환경 설정

### 1. Python

- Python 3.10 이상 권장

### 2. 의존성 설치

```bash
cd travel-time-collector
pip install -r requirements.txt
```

### 3. API 키 발급 및 환경 변수

**자동차 (필수)**

1. [카카오 개발자 콘솔](https://developers.kakao.com/) 로그인
2. 앱 생성 후 **카카오모빌리티** 길찾기 API 사용 설정
3. REST API 키 복사

**대중교통 (선택)**

1. [ODsay LAB](https://lab.odsay.com/) 회원가입
2. API 키 발급 (대중교통 길찾기 사용)

`.env` 파일 생성:

```bash
cp .env.example .env
# .env 편집: KAKAO_REST_API_KEY, ODSAY_API_KEY 입력
```

또는 터미널에서:

```bash
export KAKAO_REST_API_KEY=your_kakao_rest_api_key
export ODSAY_API_KEY=your_odsay_api_key   # 선택
```

`.env` 자동 로드는 `python-dotenv`로 하려면 코드에서 `load_dotenv()`를 호출해야 합니다. 현재는 **환경 변수**만 사용하므로 `export` 또는 `.env`를 shell에서 `source` 해서 사용하세요. (아래 실행 예시에 `dotenv` 로드 추가 가능)

### 4. 실행

**1회만 수집**

```bash
python run_once.py
```

**10분마다 수집 (스케줄러)**

```bash
python run_scheduler.py
```

- 수집 결과 **JSON 한 줄**은 **stdout**에 출력됩니다.
- 일반 로그(INFO 등)는 **stderr**에 출력됩니다.
- Datadog 연동 시 stdout JSON만 수집하도록 설정하면 됩니다.

### 5. 출력 예시 (stdout 한 줄)

```json
{"service": "travel-time-collector", "collect_time_iso": "2025-02-22T12:00:00.123456+00:00", "origin": "빗썸금융타워", "routes": [{"destination": "판교역", "car_duration_sec": 1842, "transit_duration_sec": 2580, "car_duration_min": 30.7, "transit_duration_min": 43.0}, {"destination": "광화문역", "car_duration_sec": 1200, "transit_duration_sec": 2100, "car_duration_min": 20.0, "transit_duration_min": 35.0}, ...]}
```

- `car_duration_sec` / `transit_duration_sec`: 소요시간(초)
- `car_duration_min` / `transit_duration_min`: 소요시간(분, 소수)
- API 실패 시 해당 필드는 `null`

## 프로젝트 구조

```
travel-time-collector/
├── config/
│   └── locations.py   # 출발지·목적지 좌표
├── src/
│   ├── kakao_client.py   # 카카오모빌리티 자동차 길찾기
│   ├── odsay_client.py   # ODsay 대중교통 길찾기
│   └── collector.py      # 수집 및 JSON 로그 출력
├── run_once.py        # 1회 수집
├── run_scheduler.py   # 10분 간격 스케줄
├── requirements.txt
├── .env.example
└── README.md
```

## EKS 배포

- **Dockerfile** 및 **Kubernetes 매니페스트**는 프로젝트 루트 `k8s/travel-time-collector/` 및 이 디렉터리의 `Dockerfile` 참고.
- **Deployment**: 상시 1 Pod, **매 시간 정각(KST)**에 `run_hourly.py` → `run_once` 실행.
- **CronJob**: **한국 시간 월~금 09:00~18:00** 구간에서 **:20, :40**에만 `run_once.py` 실행 (보충).
- 상세 절차: [../docs/EKS_DEPLOY_GUIDE.md](../docs/EKS_DEPLOY_GUIDE.md)

## Datadog 연동

- EKS에 배포 후 **Datadog Agent** 설치 및 로그 수집 → [../docs/DATADOG_EKS_SETUP.md](../docs/DATADOG_EKS_SETUP.md)
- stdout JSON 파이프라인 파싱 및 `routes[].car_duration_min`, `transit_duration_min` 등으로 대시보드 구성

## 참고

- 출발지 좌표(빗썸금융타워)는 `config/locations.py`에서 수정 가능합니다.
- ODsay `totalTime`은 문서에 따라 분/초가 다를 수 있어, 코드에서 분 단위일 경우 초로 변환합니다.
