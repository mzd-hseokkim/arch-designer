# ADR-0005: Deployment topology = Multi-AZ, single region (ap-northeast-2)

- **Status**: accepted
- **Date**: 2026-05-17
- **Deciders**: arch-designer (LLM-proposed, pending human review)

## Context
SLA 99.9% (§3.5), data residency KR (§3.6), budget <$3K/mo (constraints). 10K DAU, all users in Korea.

## Decision
Single AWS region **ap-northeast-2 (Seoul)** with **3 Availability Zones**. ECS services run with `desiredCount ≥ 2` spread across AZs. Aurora Multi-AZ writer + reader in different AZ. ALB across all 3 AZs. No multi-region.

On-prem DR (per portability targets): cold standby — nightly logical PG dump + container images mirrored to internal registry. Manual cutover documented; not in scope for this IaC pass.

## Consequences
**Positive**
- 99.9% SLA achievable with Multi-AZ (single-region AZ outage = ~1 hour/year worst case).
- Data residency met (region in Korea).
- Cost stays under budget — multi-region would ~2× managed-service costs.

**Negative**
- ap-northeast-2 region-wide outage = full unavailability. Accepted given SMB risk tolerance and budget.
- Cross-region DR is a documented manual procedure, not automated.

## Alternatives Considered
| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Multi-region active-active | ~99.99%, fastest recovery | Cost, cross-region replication complexity, low marginal value for SMB SLA | Cost/complexity unjustified |
| Single-AZ | Cheapest | Misses 99.9% SLA on any AZ event | Hard rejection by SLA |
| Multi-region active-passive | RTO ~minutes for region outage | Pilot light still costly; complexity not paid for by use case | Budget |
