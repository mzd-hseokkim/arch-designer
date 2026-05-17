# ADR-0003: Datastore consolidation — fewer stores than domains

- **Status**: accepted
- **Date**: 2026-05-17

## Context
9개 도메인이지만 사용자 명시 제약: "DB는 도메인 수보다 적게, 결합도 낮은 도메인끼리 공유 허용" (§3.7). 동시에 도메인 격리(이벤트 드리븐, §3.5 fault tolerance)는 유지. 다양한 데이터 모양: 트랜잭션 / 시계열 / 이벤트 아카이브 / feature lookup.

## Decision
**4개 데이터스토어** (각 리전별 인스턴스, KR/JP 각각):

| Store | Engine | Hosted domains | Why grouped |
|---|---|---|---|
| `tx-pg` | Aurora PostgreSQL Multi-AZ | Order, Dispatch, Assignment, Pricing, Billing | 동기적 일관성 요구 + 동일 트랜잭션 경계 빈번 |
| `driver-pg` | Aurora PostgreSQL Multi-AZ | Rider, RiderCompany, Notification | 라이더 컨텍스트, 결합도 높음 |
| `tracking-store` | DynamoDB (TTL 90일) | TrackingEvent | 시계열·고쓰기·시간 기반 만료 |
| `feature-redis` | ElastiCache Redis cluster mode | RouteModel feature lookup, idempotency keys | 마이크로초 latency + ephemeral |

**스키마 격리**: 같은 PG 인스턴스 내에서도 도메인별 **schema(스키마)** 분리(`orders.`, `dispatch.`, ...). 도메인 서비스는 자기 스키마만 R/W, 타 도메인 데이터는 **이벤트로만** 받음.

이벤트 아카이브는 별도 store가 아닌 **Kafka MSK + S3 Sink Connector**로 처리 (S3 = 차가운 저장소, 의도적으로 datastore 항목에서 제외).

## Consequences
**Positive**
- DB 수 감소 ⇒ SRE 4명의 운영 표면 축소 (cluster 4개/리전, 아닌 9개).
- 같은 인스턴스 내 schema 격리로 도메인 자율성은 유지.
- 트랜잭션 일관성 필요한 그룹(Order↔Dispatch↔Assignment↔Billing)이 한 PG 안에 있어 saga 회피 가능.
- Tracking은 DynamoDB로 분리 — OLTP 트래픽 50K/s가 PG를 망치지 않음.

**Negative**
- "Database-per-service" 원칙 위반. 미래 도메인 분사 시 schema → 별 cluster 마이그레이션 비용 발생.
- 같은 cluster를 공유하는 도메인들은 Aurora major version upgrade를 동기적으로 받음.
- schema 권한 enforcement(IAM 사용자/DB role)가 코드 규약뿐 — 실수로 cross-schema query 가능. CI 정적 분석 필요.

## Alternatives Considered
| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| DB-per-service (9 PG cluster/리전) | 도메인 자율성 최대 | 18 cluster 운영, 비용 + 운영부담; saga 강제 | §3.7 사용자 명시 제약 + SRE 인력 |
| 단일 거대 PG cluster | 비용 최소 | TPS 한계 + tracking 50K/s 끌어들이면 OLTP 죽음 | §3.2 성능 |
| 모든 도메인 + tracking 통합 (Aurora) | 단순함 | Aurora가 50K writes/sec 비효율, Read replica로도 한계 | §3.2 |
| DynamoDB 전체 | 무제한 스케일 | Order↔Billing 트랜잭션 일관성 표현 어려움 (Saga 강제) | 일관성 모델 비용 |
