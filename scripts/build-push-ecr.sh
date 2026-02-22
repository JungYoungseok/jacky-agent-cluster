#!/usr/bin/env bash
# ECR 레포 생성, 이미지 빌드·푸시. 프로젝트 루트에서 실행.
set -e

AWS_REGION="${AWS_REGION:-ap-northeast-2}"
REPO_NAME="${REPO_NAME:-travel-time-collector}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}"

echo "ECR URI: $ECR_URI"

# 로그인
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# 레포 없으면 생성
aws ecr create-repository --repository-name "$REPO_NAME" --region "$AWS_REGION" 2>/dev/null || true

# 빌드 및 푸시
cd "$ROOT_DIR/travel-time-collector"
docker build -t "$REPO_NAME:latest" .
docker tag "$REPO_NAME:latest" "$ECR_URI:latest"
docker push "$ECR_URI:latest"

echo "Pushed $ECR_URI:latest"
echo "다음: 매니페스트에 이미지 반영 후 apply. 예:"
echo "  export ECR_URI=$ECR_URI"
echo "  sed -i.bak \"s|travel-time-collector:latest|\$ECR_URI:latest|g\" k8s/travel-time-collector/deployment.yaml k8s/travel-time-collector/cronjob.yaml"
echo "  kubectl apply -f k8s/travel-time-collector/"
