# EKS 클러스터 생성 가이드

빗섬타워→주요 거점 소요시간 수집 서비스를 위한 EKS 클러스터를 생성하는 단계별 가이드입니다.

---

## 1. 사전 요구사항

### 1.1 필수 도구 설치

| 도구 | 용도 | 설치 방법 |
|------|------|-----------|
| **AWS CLI v2** | AWS 리소스 관리 | [공식 설치 가이드](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| **kubectl** | Kubernetes 클러스터 제어 | `brew install kubectl` (macOS) 또는 [kubectl 설치](https://kubernetes.io/docs/tasks/tools/) |
| **eksctl** | EKS 클러스터 생성/관리 | `brew install eksctl` (macOS) 또는 [eksctl 설치](https://eksctl.io/installation/) |

```bash
# 설치 확인
aws --version
kubectl version --client
eksctl version
```

### 1.2 AWS 자격 증명 설정

```bash
# 프로파일 사용 시
export AWS_PROFILE=your-profile-name

# 또는 기본 자격 증명 설정
aws configure
# AWS Access Key ID, Secret Access Key, region(ap-northeast-2) 입력
```

### 1.3 필요한 IAM 권한

EKS 클러스터 생성에 아래 권한이 필요합니다.  
`AdministratorAccess` 또는 EKS 전용 정책(`AmazonEKSClusterPolicy` 등)이 있는 계정/역할을 사용하세요.

- `AmazonEKSClusterPolicy`
- `AmazonEKSWorkerNodePolicy`
- `AmazonEKS_CNI_Policy`
- `AmazonEC2ContainerRegistryReadOnly` (이미지 pull 시)
- EC2, VPC, IAM 관련 권한

---

## 2. 클러스터 설정 확인

프로젝트의 EKS 설정 파일: `eks_resources/eks-cluster.yaml`

| 항목 | 값 | 설명 |
|------|-----|------|
| 클러스터 이름 | `shopist-eks-dev` | 원하면 변경 가능 |
| 리전 | `ap-northeast-2` (서울) | 빗섬타워와 동일 리전 권장 |
| Kubernetes 버전 | 1.29 | |
| 노드 그룹 | `ng-general` | t3.medium 2대, 1~3 오토스케일 |

이름을 **거점 소요시간 서비스용**으로 바꾸려면:

```yaml
metadata:
  name: travel-time-eks-dev   # 예시
  region: ap-northeast-2
  version: "1.29"
```

---

## 3. EKS 클러스터 생성

### 3.1 클러스터 생성 실행

```bash
cd /Users/jacky.jung/workspace/jacky-agent-cluster
eksctl create cluster -f eks_resources/eks-cluster.yaml
```

- **소요 시간**: 약 15~25분  
- 진행 상황: CloudFormation 스택 생성 → 컨트롤 플레인 → 노드 그룹 순으로 출력됩니다.

### 3.2 생성 확인

```bash
# 클러스터 목록
eksctl get cluster

# kubeconfig 자동 설정 후 노드 확인
kubectl get nodes
kubectl get nodes -o wide
```

`kubectl get nodes`에서 노드가 `Ready`이면 정상입니다.

---

## 4. 생성 후 권장 설정

### 4.1 OIDC 공급자 (선택, Pod에 IAM 역할 부여 시)

Datadog 에이전트나 AWS API 호출 시 IRSA 사용 시 필요합니다.

```bash
eksctl utils associate-iam-oidc-provider \
  --cluster shopist-eks-dev \
  --region ap-northeast-2 \
  --approve
```

### 4.2 노드 접속 테스트

```bash
kubectl run busybox --image=busybox --restart=Never -- sleep 3600
kubectl get pods
kubectl delete pod busybox
```

---

## 5. 트러블슈팅

| 현상 | 확인/조치 |
|------|-----------|
| `eksctl create cluster` 실패 | CloudFormation 콘솔에서 실패한 스택 이벤트 확인, IAM 권한 재확인 |
| `kubectl get nodes` 빈 목록 | 노드 그룹 생성 완료까지 5~10분 대기, `eksctl get nodegroup --cluster shopist-eks-dev` 확인 |
| 권한 오류 | `aws sts get-caller-identity`로 현재 계정/역할 확인, kubeconfig의 역할이 EKS 접근 권한 있는지 확인 |
| 리전 불일치 | `eks-cluster.yaml`의 `region`과 `aws configure`/환경변수 리전이 동일한지 확인 |

---

## 6. 클러스터 삭제 (필요 시)

```bash
eksctl delete cluster -f eks_resources/eks-cluster.yaml
# 또는
eksctl delete cluster --name shopist-eks-dev --region ap-northeast-2
```

---

## 다음 단계

EKS가 준비되면:

1. **소요시간 수집 서비스**: 빗섬타워 → 주요 거점 자동차/대중교통 소요시간 10분 주기 수집 (예: Google Maps/Directions API 또는 T map API 등)
2. **Datadog 연동**: 에이전트 설치, 커스텀 메트릭/로그 전송
3. **대시보드**: 수집한 메트릭으로 Datadog 대시보드 위젯 구성

원하시면 다음으로 **수집 서비스 설계(스케줄러 + API 연동)** 또는 **Datadog 에이전트 설치** 단계 가이드도 정리해 드리겠습니다.
