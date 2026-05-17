# ADR-0002: Primary database = Aurora PostgreSQL Serverless v2

- **Status**: accepted
- **Date**: 2026-05-17
- **Deciders**: arch-designer (LLM-proposed, pending human review)

## Context
RPO 5 min, RTO 30 min, SLA 99.9% (requirements §3.5). PII data, K-ISMS target (§3.6). Peak ~200 TPS but uneven (점심/저녁 spike, idle overnight). Budget <$3K/mo (constraints).

## Decision
Use **Amazon Aurora PostgreSQL Serverless v2** in Multi-AZ, with continuous backup (PITR) and automated snapshots. Min ACU 0.5, max ACU 4 (right-sized for scenario; revisit after 1 month observability).

## Consequences
**Positive**
- Continuous backup → RPO 5 min met without operator action.
- Multi-AZ writer failover ≤ 60s ⇒ RTO 30 min easily met.
- ACU auto-scales with 점심/저녁 spike; idle hours stay near min ACU (cost).
- PostgreSQL = team-familiar, OSS-compatible ⇒ on-prem DR path is plain PostgreSQL.

**Negative**
- Aurora Serverless v2 pricier per ACU-hour than provisioned at sustained load — acceptable due to spiky pattern.
- AWS-specific; on-prem DR uses logical replication to vanilla PostgreSQL, not bit-identical.

## Alternatives Considered
| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| RDS PostgreSQL provisioned (Multi-AZ) | Cheaper at sustained load | Manual scaling for spikes; RPO without continuous backup is harder | Spiky workload + RPO 5min favors Aurora |
| DynamoDB | Serverless, ms latency, infinite scale | Order data has relational queries (joins, reports) — modeling pain | Wrong shape for the data |
| PostgreSQL on ECS + EFS | Cheapest, fully portable | Team must own HA, backups, upgrades | Maintainability cost too high for 4-person team |
