# ADR-0001: Compute = Amazon EKS

- **Status**: accepted
- **Date**: 2026-05-17

## Context
35명 팀, 회사 표준 K8s (§3.7). 9개 도메인 서비스 + ML 추론 + 데이터 처리 워커를 같은 cluster에서 운영. 일 1~3회 배포 cadence가 12명 백엔드와 4명 SRE에 분산되어야 함. K8s 생태계(HPA, NetworkPolicy, ArgoCD, Istio 등) 활용 전제.

## Decision
**Amazon EKS** (managed control plane) + **managed node groups**(범용 워크로드) + **Karpenter**(autoscaling, spot 활용). 데이터 평면은 KR/JP 리전 각각 별도 cluster.

## Consequences
**Positive**
- K8s 표준 — 팀이 이미 익숙, ArgoCD/Istio 등 OSS 그대로 적용.
- ML 추론(in-cluster Triton)과 애플리케이션 같은 cluster에서 통합 운영.
- Karpenter + Spot으로 변동 트래픽 대응, 비용 절감.
- HPA + KEDA로 Kafka lag 기반 워커 스케일링.

**Negative**
- 컨트롤 플레인 비용 ($73/cluster/월 × 2 리전).
- 운영 부담은 Fargate/ECS 대비 큼 (애드온 patch, security policy, etc.) — SRE 4명에 정당화됨.

## Alternatives Considered
| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| ECS Fargate | 운영 부담 최소 | K8s 생태계(Karpenter, KEDA, Istio) 미적용. 팀 표준과 불일치 | §3.7 회사 표준 K8s |
| EKS Fargate | K8s API + serverless | Karpenter 사용 불가, 가격이 spot보다 높음 | 비용 + flexibility |
| 자체관리 K8s on EC2 (kops) | 완전 통제 | 컨트롤 플레인 운영 부담, EKS 대비 이득 없음 | 운영 비용 |
