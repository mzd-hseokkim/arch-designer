# ADR-0004: Multi-region topology — per-country active, async global aggregation

- **Status**: accepted
- **Date**: 2026-05-17

## Context
KR + JP 동시 운영, 데이터 주권 per-country (§3.6 / §3.8). 라이더·주문은 각 국가 내부에서만 발생 (현재 가정 — open question 5에 명시). SLA 99.95%, RTO 15분 (§3.5). 분석/ML 학습은 글로벌 통합 데이터 필요.

## Decision
**리전 = 데이터 주권 경계**. 리전별 self-sufficient stack:
- `ap-northeast-2` (KR): 자체 EKS + MSK + Aurora + DynamoDB + S3
- `ap-northeast-1` (JP): 동일 stack

**Active-active**: 각 리전은 자국 트래픽만 처리. 단일 리전 장애 시에도 타국은 영향 없음 (격리). 한 리전이 다른 리전 트래픽을 받지 않음 (데이터 주권 위반 회피).

**글로벌 통합**: 양 리전의 S3 (이벤트 아카이브) → **분석 전용 us-west-2 데이터 레이크**로 일방향 sink (개인정보 비식별화 후). ML 학습/BI는 여기서만 수행. 운영 데이터는 통합하지 않음.

**DNS / 라우팅**: Route 53 latency-based + geofence (KR 트래픽은 KR 리전으로 강제, IP 추정 실패 시 사용자 명시).

**리전 내 가용성**: ADR-0001/0002 따라 Multi-AZ. 따라서 99.95% SLA는 리전 내 Multi-AZ만으로 달성 가능 — 리전 단위 DR은 RTO 15분 이내 자동 복구가 아닌 **수동 declared disaster** 절차로 수용 (해당 리전 사용자는 다운).

## Consequences
**Positive**
- 데이터 주권 자동 enforcement — cross-region write 자체가 발생하지 않음.
- 리전 격리로 blast radius 최소화.
- 분석은 비식별화 후 단일 레이크에 통합 — ML 학습 데이터 부족 문제 회피.

**Negative**
- 리전 단위 장애 = 해당 국가 다운. 99.95% SLA가 리전 가용성에 의존.
- 운영 복잡도 2× (배포 파이프라인이 양 리전에 거의 독립적으로 도달해야 함).
- 글로벌 라이더(KR-JP 크로스보더) 케이스는 미해결 — open question으로 남김.

## Alternatives Considered
| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Active-passive (KR primary, JP cold standby) | 비용 ↓ | JP 트래픽이 KR에 노출 = 데이터 주권 위반 | §3.6 |
| Active-active with cross-region replication | 리전 장애 시에도 가용 | KR 데이터 JP에 복제 = 위반. RPO 1분 cross-region 비용 폭주 | §3.6 + 비용 |
| Single region (KR only, JP은 향후) | 가장 단순 | JP 출시 일정 제약 — 비즈니스 요구와 충돌 | 비즈니스 |
| Multi-cloud failover | 극한 가용성 | 99.95% SLA에 불필요, vendor lock-in tolerance medium | 과설계 |
