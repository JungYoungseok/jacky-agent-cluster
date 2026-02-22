# EKS 배포 가이드 (travel-time-collector)

Deployment(매 시 정각) + CronJob(월~금 09~18시 :20·:40)을 EKS에 올리고, **이미지는 ECR**에 푸시합니다.

---

## 0. 로컬에서 Deployment 동작 확인 (권장)

EKS에 올리기 전에 로컬에서 **Deployment와 동일한 동작**(`run_hourly.py` → `run_once`)이 되는지 확인하세요.

### 0.1 Python으로 확인

```bash
cd travel-time-collector
# .env 또는 환경변수로 KAKAO_REST_API_KEY, ODSAY_API_KEY 설정 후
RUN_FIRST_IMMEDIATELY=1 python run_hourly.py
```

- `RUN_FIRST_IMMEDIATELY=1` 이면 **첫 실행을 곧바로** 한 번 하고, 그다음부터는 매 시 정각에만 실행합니다.
- **stdout에 JSON 한 줄**이 나오면 성공. 확인 후 Ctrl+C로 종료.

### 0.2 Docker 이미지로 확인 (선택)

Deployment와 동일한 이미지·CMD로 실행해 봅니다.

```bash
cd travel-time-collector
docker build -t travel-time-collector:latest .
docker run --rm --env-file .env -e RUN_FIRST_IMMEDIATELY=1 travel-time-collector:latest
```

- **바로** `travel-time-collector hourly started ...` 가 나오고, API 호출 후(1~2분 내) stdout에 **JSON 한 줄**이 나오면 정상입니다.
- 에러가 나면 stderr에 출력되므로, 확인하려면 `docker run ... 2>&1` 로 실행하세요.

---

## 1. 사전 조건

- EKS 클러스터 생성 완료, `kubectl` 연결됨
- AWS CLI 설정 (ECR 푸시 권한), Docker 실행 중
- API 키: Kakao REST API, ODsay API

---

## 2. 이미지 레지스트리: ECR

이미지는 **Amazon ECR**만 사용합니다.

### 2.1 한 번에 빌드·푸시 (권장)

프로젝트 **루트**에서:

```bash
./scripts/build-push-ecr.sh
```

- `AWS_REGION` 기본값: `ap-northeast-2` (리전 변경 시 `AWS_REGION=us-east-1 ./scripts/build-push-ecr.sh`)
- ECR 로그인 → 레포 `travel-time-collector` 없으면 생성 → `travel-time-collector/` 기준 빌드 → `$ECR_URI:latest` 푸시

### 2.2 수동으로 할 때

```bash
AWS_REGION=ap-northeast-2
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/travel-time-collector

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
aws ecr create-repository --repository-name travel-time-collector --region $AWS_REGION 2>/dev/null || true

cd travel-time-collector
docker build -t travel-time-collector:latest .
docker tag travel-time-collector:latest $ECR_URI:latest
docker push $ECR_URI:latest
```

---

## 3. Kubernetes 리소스 배포

### 3.1 Secret 생성 (API 키, 최초 1회)

```bash
kubectl create secret generic travel-time-collector-secret \
  --namespace=travel-time \
  --from-literal=KAKAO_REST_API_KEY=실제_카카오_키 \
  --from-literal=ODSAY_API_KEY=실제_ODsay_키
```

(이미 있으면 생략)

### 3.2 ECR 이미지로 한 번에 배포 (권장)

빌드·푸시 후 **이미지 자동 치환**하여 apply:

```bash
./scripts/deploy-ecr.sh
```

- `build-push-ecr.sh` 실행 → ECR 푸시
- `namespace`, `configmap`, `deployment`, `cronjob` apply 시 `image`를 `$ECR_URI:latest`로 치환 (로컬 yaml 파일은 수정하지 않음)

### 3.3 수동 apply

```bash
kubectl apply -f k8s/travel-time-collector/namespace.yaml
kubectl apply -f k8s/travel-time-collector/configmap.yaml

# 이미지만 ECR URI로 치환해서 적용
ECR_URI=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.ap-northeast-2.amazonaws.com/travel-time-collector
sed "s|travel-time-collector:latest|${ECR_URI}:latest|g" k8s/travel-time-collector/deployment.yaml | kubectl apply -f -
sed "s|travel-time-collector:latest|${ECR_URI}:latest|g" k8s/travel-time-collector/cronjob.yaml | kubectl apply -f -
```

### 3.4 확인

```bash
kubectl -n travel-time get pods
kubectl -n travel-time get cronjob
kubectl -n travel-time logs -l app=travel-time-collector --tail=50
```

- **Deployment**: 상시 1 Pod. `run_hourly.py`로 **매 시간 정각(KST)**에 수집.
- **CronJob**: **한국 시간 월~금 09:00~18:00** 구간에서만 **:20분, :40분**에 `run_once.py` 실행 (데이터 보충).

---

## 4. Datadog 연동

- **Agent 설치 및 로그 수집**: [docs/DATADOG_EKS_SETUP.md](./DATADOG_EKS_SETUP.md) 참고.
- Deployment/CronJob Pod에 이미 `ad.datadoghq.com/...logs` annotation이 있으므로, Agent가 로그를 수집하면 `service:travel-time-collector`로 보입니다.
- Datadog에서 파이프라인(JSON 파싱) + 대시보드 설정하면 됩니다.

---

## 5. 디렉터리 구조

```
scripts/
├── build-push-ecr.sh   # ECR 로그인·레포 생성·빌드·푸시
└── deploy-ecr.sh      # 빌드·푸시 후 이미지 치환하여 apply
k8s/travel-time-collector/
├── namespace.yaml
├── configmap.yaml
├── secret.yaml.example
├── deployment.yaml
└── cronjob.yaml
travel-time-collector/
├── Dockerfile
├── run_once.py
├── run_hourly.py
├── config/
└── src/
```

- 매니페스트의 `image: travel-time-collector:latest`는 **apply 시** 스크립트가 ECR URI로 치환합니다. 저장소에는 그대로 두면 됩니다.

---

## 6. 트러블슈팅

| 현상 | 확인 |
|------|------|
| ImagePullBackOff | ECR URI 확인, 노드 IAM에 `AmazonEC2ContainerRegistryReadOnly` 등 ECR pull 권한 필요 (eksctl 기본 노드 그룹은 보통 포함) |
| CrashLoopBackOff | `kubectl logs`로 stderr 확인, Secret 키 이름/환경변수 확인 |
| 로그가 Datadog에 안 보임 | Agent 로그 수집 활성화, Pod annotation, 파이프라인 필터 확인 |
