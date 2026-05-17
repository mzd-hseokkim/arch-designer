# dispatch-hub — Design Document

## 1. Introduction & Goals
B2B 실시간 라스트마일 배송 디스패치 SaaS, 한국·일본 동시 운영. 이벤트 드리븐 9-도메인 MSA on Kafka, 4-개 데이터스토어로 통합.

**Top quality goals**
1. **Reliability** — 99.95% SLA, 도메인 격리, 데이터 주권 per-country
2. **Performance** — ingest 3K TPS, tracking 50K events/sec, assignment latency < 5s
3. **Maintainability** — 35명 팀이 9 서비스 + 2 리전 운영. **DB 수 < 도메인 수**로 운영 표면 축소

## 2. Constraints
- 회사 표준 K8s
- 데이터 주권: KR 데이터는 KR 리전, JP 데이터는 JP 리전 — cross-region 운영 데이터 복제 금지
- 결제 미보유 → PCI 회피, 단 PII + 위치 데이터 보호 K-ISMS + APPI
- 사용자 명시: 도메인 9개지만 DB는 더 적게 (결합도 낮은 도메인 공유)
- multi-cloud 불필요

## 3. Solution Strategy
- **EKS 기반 MSA** ([ADR-0001](docs/adr/0001-compute-eks.md))
- **MSK Kafka 이벤트 백본**, canonical Avro + Glue Schema Registry ([ADR-0002](docs/adr/0002-event-backbone-msk.md))
- **4 datastore consolidation** by coupling, 도메인은 schema 격리로 자율성 유지 ([ADR-0003](docs/adr/0003-datastore-consolidation.md))
- **리전 = 데이터 주권 경계**, per-region self-sufficient, 분석만 글로벌 데이터 레이크로 일방향 sink ([ADR-0004](docs/adr/0004-multi-region-topology.md))
- **부수 결정** (no ADR):
  - API Gateway: Kong on EKS (Istio mesh와 통합)
  - 클라이언트 인증: Cognito (EC 기업 API Key + HMAC, 라이더 OIDC)
  - ML 추론: in-cluster Triton (저지연), 학습: SageMaker batch
  - Observability: Prometheus + Grafana + Loki + Tempo (Grafana Cloud는 미사용 — 데이터 주권)
  - CI/CD: GitHub Actions → ECR → ArgoCD pull
  - DR: 리전 단위 declared disaster, 자동 failover 없음 (ADR-0004 수용)

## 4. Building Block View

### 4.1 Level 1: System Context
| Actor / System | Interaction |
|---|---|
| EC 기업 | HTTPS REST + Webhook (in/out) |
| 라이더 (모바일) | gRPC over TLS, OIDC + 디바이스 바인딩 |
| 엔드유저 (추적) | HTTPS, signed URL |
| 라이더 회사 관리자 | HTTPS 웹 |
| 운영자 | 내부 admin 콘솔 (VPN) |
| PG | inbound webhook |
| FCM/APNs | outbound push |
| Map provider | outbound API (route, geocoding) |

### 4.2 Level 2: Containers (9 domain services + supporting)

| Service | Tech | DB(schema) | ADR |
|---|---|---|---|
| `order-svc` | Java / Spring Boot | tx-pg(orders) | ADR-0001, ADR-0003 |
| `dispatch-svc` | Java / Spring Boot | tx-pg(dispatch) | ADR-0001, ADR-0003 |
| `assignment-svc` | Java / Spring Boot | tx-pg(assignments) | ADR-0001, ADR-0003 |
| `pricing-svc` | Java / Spring Boot | tx-pg(pricing) | ADR-0001, ADR-0003 |
| `billing-svc` | Java / Spring Boot | tx-pg(billing) | ADR-0001, ADR-0003 |
| `rider-svc` | Go | driver-pg(rider) | ADR-0001, ADR-0003 |
| `notification-svc` | Go | driver-pg(notification) | ADR-0001, ADR-0003 |
| `tracking-svc` | Go (gRPC, 저지연) | tracking-store (DynamoDB) | ADR-0001, ADR-0003 |
| `routing-ml-svc` | Python + Triton | feature-redis | ADR-0001 |
| **Supporting** | | | |
| `kong-gateway` | Kong on K8s | — | (prose) |
| `ingest-api` | Go (REST/Webhook 수신) | — (writes to Kafka) | ADR-0002 |
| `archive-sink` | Kafka Connect S3 sink | S3 (events archive) | ADR-0002 |
| `analytics-sink` | replication → 글로벌 lake | — | ADR-0004 |

### 4.3 Datastores (per-region)
| Store | Engine | Hosted schemas | Why grouped (ADR-0003) |
|---|---|---|---|
| `tx-pg` | Aurora PG | orders, dispatch, assignments, pricing, billing | 동기 일관성 + 같은 트랜잭션 경계 |
| `driver-pg` | Aurora PG | rider, rider_company, notification | 라이더 컨텍스트 결합 |
| `tracking-store` | DynamoDB | TrackingEvent (TTL 90d) | 시계열·고쓰기·시간 만료 |
| `feature-redis` | ElastiCache Redis cluster mode | feature lookup, idempotency | μs latency |

## 5. Runtime View

### 5.1 시나리오 A: 주문 인입 → 배차 → 라이더 push
1. EC 기업 → `ingest-api` REST 호출 (API Key + HMAC 검증).
2. `ingest-api` → Kafka `orders.events.v1` publish (canonical Avro).
3. `order-svc` consume → `tx-pg.orders` 저장, `OrderCreated` 발행.
4. `dispatch-svc` consume → 후보 라이더 조회 (`rider-svc` gRPC 호출), `routing-ml-svc`에 스코어링 요청 (in-cluster, gRPC).
5. 최적 라이더 결정 → `assignments.events.v1`에 `AssignmentProposed` 발행.
6. `assignment-svc` → `tx-pg.assignments` 저장, `notification-svc`에 push 트리거.
7. `notification-svc` → FCM/APNs 호출 → 라이더 앱 도착. 5초 이내 SLO.

### 5.2 시나리오 B: 트래킹 핑 50K/s
1. 라이더 앱 → `tracking-svc` gRPC stream (저지연).
2. `tracking-svc` → DynamoDB write (`tracking-store`, partition key = rider_id + time bucket).
3. **선택적** Kafka `tracking.pings.v1` 발행 (6h retention) — 다른 컨슈머 없으면 skip 가능.
4. 의미있는 상태 변화 (출발/도착/이탈)만 `tracking.events.v1`에 별도 발행 (30d retention).
5. 추적 페이지: `tracking-svc`가 signed URL의 토큰 검증 후 최근 핑을 SSE로 송출.

### 5.3 시나리오 C: 단일 도메인 서비스 장애
1. `notification-svc` crash loop. 라이더 push 지연.
2. `assignment-svc`는 정상 — 배차 자체는 진행, push 메시지가 Kafka에 적재.
3. `notification-svc` 복구 → consumer offset에서 재개, 누락 push 일괄 전송.
4. CloudWatch/Prometheus 알람 (consumer lag > N) → 운영자 통지.
5. 핵심 흐름(주문 인입 + 배차)는 영향 없음 — §3.5 graceful degradation 충족.

### 5.4 시나리오 D: ML 라우팅
- **추론**: `dispatch-svc` → in-cluster `routing-ml-svc` (Triton) → ETA + 점수 반환. p99 < 100ms.
- **학습**: 매일 03:00 KST, 비식별화된 글로벌 lake에서 SageMaker training job → 새 모델 S3 → ArgoCD가 Triton 모델 디렉토리 sync → blue/green 배포.

## 6. Deployment View

### 6.1 AWS (per-region, KR & JP 동일 구조)
- **EKS cluster** (1.30+), managed node group + Karpenter (Spot 비중 50%).
- **MSK**: 3-broker provisioned, Multi-AZ. Glue Schema Registry.
- **Aurora PG**: 2 cluster (`tx-pg`, `driver-pg`), Multi-AZ writer + reader.
- **DynamoDB**: `tracking-store`, on-demand capacity, TTL 90d.
- **ElastiCache Redis**: cluster mode enabled, 3-shard × 2-replica.
- **S3**: events archive bucket (region-local) + 비식별화 sink to us-west-2 lake.
- **API Gateway**: AWS API Gateway 미사용, **Kong on EKS** + ALB Ingress.
- **Cognito User Pool**: 라이더(OIDC) + 라이더회사 관리자.
- **VPC**: 3 AZ, public/private/isolated subnet 분리, PrivateLink로 외부 SDK 통신.
- **Route 53**: latency-based + geo-fence (KR/JP 라우팅).
- **CI/CD**: GitHub Actions → ECR (region-local) → ArgoCD pull.
- **Observability**: Prometheus + Grafana + Loki + Tempo on EKS (cluster-local).

→ `diagrams/deployment-aws.py`

### 6.2 Kubernetes (workload zoom-in, AWS-agnostic)
- **Namespaces**: `gateway`, `domain-tx`, `domain-driver`, `domain-tracking`, `ml`, `obs`, `argo`.
- **Ingress**: Kong Gateway (HTTPRoute), ALB Ingress controller.
- **Workloads**: Deployment + HPA(CPU/mem) + **KEDA**(Kafka consumer lag).
- **Service mesh**: Istio sidecar (mTLS, traffic shifting for ML model deploy).
- **Secrets**: External Secrets Operator → AWS Secrets Manager.
- **Pod security**: PodSecurityStandards `restricted`, NetworkPolicy 도메인 NS 간 차단.
- **GitOps**: ArgoCD ApplicationSet per region.

→ `diagrams/deployment-k8s.py`

### 6.3 글로벌 데이터 레이크 (us-west-2, 비운영)
- S3 (raw zone) ← 비식별화된 KR/JP events
- AWS Glue + Iceberg
- SageMaker training jobs
- BI: Redshift Serverless
- **운영 트래픽 0**. 분석/ML 전용. SLA 99.5% 수용.

## 7. Architecture Decisions
| # | Decision | Status |
|---|---|---|
| [ADR-0001](docs/adr/0001-compute-eks.md) | Compute = Amazon EKS | accepted |
| [ADR-0002](docs/adr/0002-event-backbone-msk.md) | Event backbone = Amazon MSK | accepted |
| [ADR-0003](docs/adr/0003-datastore-consolidation.md) | Datastore = 4 stores (consolidated from 9 domains) | accepted |
| [ADR-0004](docs/adr/0004-multi-region-topology.md) | Topology = per-country active, async global aggregation | accepted |
