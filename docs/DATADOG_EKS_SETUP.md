# Datadog Agent + 로그 연동 (EKS)

EKS에서 travel-time-collector 로그를 Datadog으로 보내고, 대시보드에서 소요시간을 보려면 아래 순서로 설정합니다.

---

## 1. Datadog Agent 설치 (EKS)

### 1.1 Helm으로 설치

```bash
helm repo add datadog https://helm.datadoghq.com
helm repo update
```

`values-datadog.yaml` 예시 (API 키·사이트는 본인 값으로):

```yaml
datadog:
  site: datadoghq.com  # 또는 ap1.datadoghq.com 등
  apiKey: <DATADOG_API_KEY>
  logs:
    enabled: true
    containerCollectAll: true
  apm:
    enabled: true
  processAgent:
    enabled: true
```

```bash
kubectl create namespace datadog
helm install datadog-agent datadog/datadog -n datadog -f values-datadog.yaml
```

### 1.2 로그 수집 확인

- Pod/Deployment에 **annotation**으로 로그 소스 지정 가능 (이미 deployment/cronjob에 추가됨):
  - `ad.datadoghq.com/<container>.logs: '[{"source": "travel-time-collector", "service": "travel-time-collector"}]'`
- `containerCollectAll: true`면 모든 컨테이너 stdout/stderr를 수집합니다.

---

## 2. 로그 파이프라인 (JSON 파싱)

collector가 **stdout**에 한 줄 JSON으로 출력합니다. Datadog에서 파싱해 필드를 쿼리/대시보드에 쓰려면 파이프라인을 추가합니다.

1. **Datadog** → **Logs** → **Pipelines**
2. **New Pipeline** → Name: `travel-time-collector`
3. **Filter**: `service:travel-time-collector`
4. **Processor** 추가:
   - **JSON Parser** (또는 Grok):  
     - 소스 속성: `message` (또는 `@message`)  
     - 한 줄이 하나의 JSON이므로 **JSON Parser**로 파싱
   - 파싱 후 `collect_time_iso`, `origin`, `routes` (배열) 등이 필드로 나옵니다.

**Grok 예시** (JSON 한 줄이 `message`에 있을 때):

```
Parsing rule: JSON
예: @message 파싱 후 → routes[0].car_duration_min, routes[0].transit_duration_min 등
```

실제로는 **Processor**에서 **JSON Parser** 선택 후, **심볼**을 `@message` 또는 `message`로 두면 됩니다.

---

## 3. 대시보드에서 쓰기

- **Logs** → **Explorer**에서 `service:travel-time-collector` 로 검색.
- 파이프라인으로 파싱된 뒤에는:
  - `@routes.destination`, `@routes.car_duration_min`, `@routes.transit_duration_min` 등으로 필터/그래프 가능.
- **Dashboard** → **New Dashboard** → **New Widget**:
  - **Timeseries** / **Query Value**:  
    메트릭이 필요하면 Log-based Metric을 만들고,  
    또는 **Logs** 위젯으로 최근 수집 결과 테이블 표시.

(선택) **Log-based Metric**:
- **Logs** → **Generate Metrics** → `service:travel-time-collector` 기준으로  
  `routes.car_duration_min`, `routes.transit_duration_min` 등 집계 메트릭 생성 후 대시보드에 추가.

---

## 4. 요약

| 항목 | 내용 |
|------|------|
| Agent | Helm으로 설치, `logs.enabled: true`, 필요 시 `containerCollectAll: true` |
| 로그 소스 | Deployment/CronJob Pod annotation으로 `source`/`service` 지정 (이미 적용됨) |
| 파이프라인 | `service:travel-time-collector` 필터 + JSON Parser로 stdout 한 줄 파싱 |
| 대시보드 | 파싱 필드 또는 Log-based Metric으로 시계열/테이블 구성 |

API 키는 Helm values에서 Secret으로 관리하거나, AWS Secrets Manager 등과 연동해 사용하는 것을 권장합니다.
