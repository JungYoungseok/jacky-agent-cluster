#!/usr/bin/env bash
# ECR 빌드·푸시 후 k8s 매니페스트에 이미지 반영하여 apply. 프로젝트 루트에서 실행.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
K8S_DIR="$ROOT_DIR/k8s/travel-time-collector"

# 1) ECR 빌드·푸시
"$SCRIPT_DIR/build-push-ecr.sh"

# 2) ECR_URI 설정 (build-push-ecr.sh와 동일 로직)
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
REPO_NAME="${REPO_NAME:-travel-time-collector}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}"

# 3) apply (이미지만 ECR URI로 치환하여 파이프로 전달, 로컬 파일은 수정하지 않음)
kubectl apply -f "$K8S_DIR/namespace.yaml"
kubectl apply -f "$K8S_DIR/configmap.yaml"
sed "s|travel-time-collector:latest|${ECR_URI}:latest|g" "$K8S_DIR/deployment.yaml" | kubectl apply -f -
sed "s|travel-time-collector:latest|${ECR_URI}:latest|g" "$K8S_DIR/cronjob.yaml" | kubectl apply -f -

# deployment 스펙이 바뀌지 않아도(:latest 동일) 새 이미지로 Pod 재기동
kubectl rollout restart deployment/travel-time-collector -n travel-time
kubectl rollout status deployment/travel-time-collector -n travel-time --timeout=120s

echo "Deployed. Secret이 없으면 생성: kubectl create secret generic travel-time-collector-secret -n travel-time --from-literal=KAKAO_REST_API_KEY=... --from-literal=ODSAY_API_KEY=..."
