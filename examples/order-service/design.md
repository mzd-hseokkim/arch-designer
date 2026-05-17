# Order Service — Design Document

## 1. Introduction & Goals
SaaS form 다중 채널 주문 관리 서비스 (네이버 스마트스토어 / 쿠팡 / 자사몰 통합). 한국 SMB 셀러 대상.

**Top quality goals**
1. **Reliability** — SLA 99.9%, 단일 채널 장애가 전체로 번지지 않음 (RPO 5분 / RTO 30분)
2. **Performance** — 대시보드 p99 < 300ms at 200 TPS peak (점심/저녁)
3. **Maintainability** — 4인 팀이 운영 가능한 운영 부담, 신규 채널 어댑터를 plug-in 형태로 확장

## 2. Constraints
- 데이터 주권: ap-northeast-2 강제 (K-ISMS 목표)
- 예산: $3000/mo 이하 — 매니지드 활용하되 무절제 금지
- 팀: 4명, AWS 익숙. K8s/Kafka 같은 운영 부담 큰 스택 회피
- 결제 미보유 → PCI 적용 회피, 단 PII 보호는 K-ISMS 수준
- 핵심 비즈니스 로직은 컨테이너 이식 가능해야 함 (on-prem DR 옵션)

## 3. Solution Strategy
- **컨테이너 기반 컴퓨트** — ECS Fargate, on-prem에서는 같은 이미지로 docker-compose ([ADR-0001](docs/adr/0001-compute-ecs-fargate.md))
- **이벤트 드리븐 채널 분리** — 채널당 독립 어댑터 + SQS, 장애 격리 ([ADR-0003](docs/adr/0003-channel-adapters-event-driven.md))
- **Spiky 워크로드용 서버리스 DB** — Aurora Serverless v2, 자동 백업으로 RPO ([ADR-0002](docs/adr/0002-database-aurora-serverless-v2.md))
- **관리형 인증** — Cognito User Pool + MFA, 셀러/직원 RBAC ([ADR-0004](docs/adr/0004-auth-cognito.md))
- **Multi-AZ 단일 리전** — 99.9% SLA를 비용 안에서 달성 ([ADR-0005](docs/adr/0005-deployment-multi-az-single-region.md))
- **부수 결정** (no ADR): GitHub Actions CI/CD, CloudWatch + Container Insights, SNS Mobile Push (FCM bridge), ALB만 사용(API Gateway 생략)

## 4. Building Block View

### 4.1 Level 1: System Context
| Actor / System | Interaction |
|---|---|
| Seller (web/mobile) | HTTPS, Cognito 인증 |
| 네이버 스마트스토어 | API polling |
| 쿠팡 WING | API polling |
| 자사몰 | webhook 송신 |
| PG | webhook (결제 결과) |
| FCM | push 발송 |

### 4.2 Level 2: Containers
| Name | Tech | Responsibility | ADR |
|---|---|---|---|
| `web-app` | React SPA on S3 + CloudFront | 셀러 대시보드 UI | — |
| `api-gateway-svc` | Java / Spring Boot on Fargate | REST API, Cognito JWT 검증, 라우팅 | ADR-0001, ADR-0004 |
| `naver-adapter` | Python on Fargate | 네이버 주문 polling, normalize, SQS publish | ADR-0001, ADR-0003 |
| `coupang-adapter` | Python on Fargate | 쿠팡 주문 polling, normalize, SQS publish | ADR-0001, ADR-0003 |
| `ownsite-adapter` | Python on Fargate | 자사몰 webhook 수신, normalize, SQS publish | ADR-0001, ADR-0003 |
| `order-ingest` | Java / Spring Boot on Fargate | SQS 다중 큐 consume, DB 저장, 도메인 이벤트 발행 | ADR-0001, ADR-0003 |
| `notification-worker` | Python on Fargate | OrderCreated 이벤트 → SNS/FCM push | ADR-0001 |
| `aurora-pg` | Aurora PG Serverless v2, Multi-AZ | OLTP 저장소 | ADR-0002, ADR-0005 |
| `redis` | ElastiCache Redis, Multi-AZ | 세션, 채널 polling 커서, 집계 캐시 | ADR-0005 |
| `cognito-pool` | Cognito User Pool | 사용자 인증, MFA, 그룹 RBAC | ADR-0004 |
| `s3-export` | S3 (KMS) | CSV/Excel export 결과물 보관 | — |
| `sqs-channel-queues` | SQS (per-channel + DLQ) | 채널 이벤트 버퍼 | ADR-0003 |

## 5. Runtime View

### 5.1 시나리오 A: 채널 주문 인입 (정상)
1. `naver-adapter`가 60초 주기로 신규 주문 polling.
2. 응답을 canonical `OrderEvent`로 정규화, `sqs-naver` 큐에 publish.
3. `order-ingest`가 큐에서 메시지 수신 → `aurora-pg`에 `INSERT` + `OrderCreated` 도메인 이벤트 발행.
4. `notification-worker`가 이벤트 수신 → 셀러 디바이스로 FCM push.
5. 대시보드 next refresh에서 셀러가 신규 주문 확인.

### 5.2 시나리오 B: 채널 장애 (쿠팡 API 5xx 폭증)
1. `coupang-adapter`가 503 응답 받음, exponential backoff로 polling 간격 늘림.
2. 큐에는 메시지 미발행, 다른 채널(`naver-adapter`, `ownsite-adapter`)은 정상 동작 — 격리 성공.
3. CloudWatch 알람(연속 5xx > 5분) → 운영자 알림.
4. API 정상화 후 backoff 해제, polling 재개. 누락 주문은 채널 API의 시간범위 query로 catch-up.

### 5.3 시나리오 C: 대시보드 조회 (피크)
1. 셀러가 대시보드 접속 → CloudFront → `web-app` (SPA 정적).
2. SPA가 `api-gateway-svc` 호출. ALB가 Fargate task 중 하나로 라우팅.
3. `api-gateway-svc`가 Cognito JWT 검증, `redis`에서 캐시된 일간 집계 조회 (hit), DB 미접근.
4. p99 < 300ms 목표 — Redis miss 시 Aurora reader endpoint 조회.

## 6. Deployment View

### 6.1 AWS (primary)
- **VPC**: 1개 VPC, 3 AZ (`ap-northeast-2a/b/c`). Public subnet (ALB, NAT), Private subnet (Fargate), Isolated subnet (Aurora, ElastiCache).
- **Edge**: Route53 → CloudFront (web-app) / ALB (api-gateway-svc).
- **Compute**: ECS Fargate cluster, 서비스별 task definition. Min 2 / Max 8 replicas, target tracking on CPU 60%.
- **Data**: Aurora Serverless v2 (writer + reader, Multi-AZ). ElastiCache Redis (cluster mode disabled, Multi-AZ).
- **Messaging**: SQS 큐 4개 (3 channel + 1 DLQ 공용). SNS Topic + Mobile Push.
- **Storage**: S3 (KMS-encrypted) — export 산출물, ALB 액세스 로그.
- **Auth**: Cognito User Pool, App Client × 2 (web/mobile).
- **Network egress**: NAT Gateway (1개 — 비용 절감, 단일 AZ 장애 시 일시적 인입 영향 수용).
- **Observability**: CloudWatch Logs + Container Insights + X-Ray (샘플링 5%).
- **Secrets**: AWS Secrets Manager.
- **CI/CD**: GitHub Actions → ECR push → ECS deploy.

→ `diagrams/deployment-aws.py` 생성 대상.

### 6.2 On-Prem (DR / 백업)
- **Compute**: docker-compose v3.8, 단일 호스트 또는 2-노드 (HA는 cold standby 수준).
- **DB**: vanilla PostgreSQL 15 + logical replication (AWS Aurora가 publisher).
- **Cache**: Redis (standalone).
- **Messaging**: RabbitMQ (SQS 대체, 어댑터 코드의 큐 추상화 레이어를 통해 교체).
- **Edge**: Nginx (TLS termination, reverse proxy).
- **Auth**: Cognito 대체로 Keycloak 사전 프로비저닝 (사용자 동기화 별도 작업).
- **Push**: 동일 FCM (인터넷 egress 필요).
- 운영 상태: cold standby. 평시는 데이터 수신만, 트래픽 cutover 시 수동 절차.

→ `diagrams/deployment-onprem.py` 생성 대상.

## 7. Architecture Decisions
| # | Decision | Status |
|---|---|---|
| [ADR-0001](docs/adr/0001-compute-ecs-fargate.md) | Compute = ECS Fargate | accepted |
| [ADR-0002](docs/adr/0002-database-aurora-serverless-v2.md) | DB = Aurora PG Serverless v2 | accepted |
| [ADR-0003](docs/adr/0003-channel-adapters-event-driven.md) | Channel adapters = isolated event-driven workers (SQS) | accepted |
| [ADR-0004](docs/adr/0004-auth-cognito.md) | Authn = Amazon Cognito | accepted |
| [ADR-0005](docs/adr/0005-deployment-multi-az-single-region.md) | Topology = Multi-AZ, single region (ap-northeast-2) | accepted |
