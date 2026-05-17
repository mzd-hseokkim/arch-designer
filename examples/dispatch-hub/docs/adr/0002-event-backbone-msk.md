# ADR-0002: Event backbone = Amazon MSK (Kafka)

- **Status**: accepted
- **Date**: 2026-05-17

## Context
50K events/sec 트래킹 핑(§3.2), 9개 도메인 간 이벤트 드리븐 통신, RPO 1분(§3.5), assignment latency 5초(§3.2). Canonical Avro 스키마(§3.3). SRE 4명 — Kafka 직접 운영은 부담.

## Decision
**Amazon MSK (provisioned)** Kafka 3.x cluster, 리전당 1개. 3-broker 시작, MSK Auto-scaling으로 storage 자동 증가. **Schema Registry**는 MSK 외부 (Confluent OSS or AWS Glue Schema Registry — 후자 채택, IAM 통합).

토픽 설계:
- `orders.events.v1` (주문 lifecycle, KR/JP 각각)
- `dispatch.events.v1`
- `assignments.events.v1`
- `tracking.pings.v1` (high-volume, 단기 retention 6h)
- `tracking.events.v1` (의미있는 상태 변화만, 30일)
- `billing.events.v1`
- DLT (Dead Letter Topics) per consumer group

## Consequences
**Positive**
- 단일 이벤트 백본 ⇒ 도메인 간 결합 낮음, 새 도메인 추가 시 기존 코드 무관.
- MSK + KEDA로 lag-driven scaling.
- Glue Schema Registry로 Avro 호환성 enforcement.
- MSK Multi-AZ 자동 — broker 1대 장애 견딤.

**Negative**
- MSK 가격: 3-broker `kafka.m7g.large` 리전당 ~$700/월 + 스토리지.
- Cross-region replication은 MirrorMaker2를 직접 운영 (MSK Replicator 사용 시 추가 비용) — KR/JP 각각 독립 cluster로 우회.

## Alternatives Considered
| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Confluent Cloud | fully managed, KSQL, 좋은 UX | $$$, 데이터가 외부 SaaS 통과 (§3.6 data residency 검토 필요) | 데이터 주권 + 비용 |
| Self-hosted Kafka on EKS | 통제 최대 | broker 운영(rebalance, upgrade, JMX 모니터링) SRE 4명에 과부담 | §3.7 |
| Kinesis Data Streams | 관리형, AWS-native | Avro 스키마/exactly-once semantics 약함, 컨슈머 라이브러리 빈약 | 9개 도메인 컨슈머 라이브러리 부재 |
| Amazon EventBridge | 서버리스, 룰 기반 | 50K/s × 9 토픽 비용 폭주, 순서 보장 부재 | TPS + ordering |
