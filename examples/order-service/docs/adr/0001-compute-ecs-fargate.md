# ADR-0001: Compute = ECS Fargate

- **Status**: accepted
- **Date**: 2026-05-17
- **Deciders**: arch-designer (LLM-proposed, pending human review)

## Context
Peak TPS 200, p99 latency 300ms (requirements §3.2). Channel polling workers need long-lived, scheduled processes. Team of 4, AWS-familiar (constraints). Budget under $3K/mo. Need on-prem portability for DR (§3.8 portability).

## Decision
Run all application services on **AWS ECS Fargate** with autoscaling. Workloads packaged as OCI container images so the same image runs on docker-compose on-prem.

## Consequences
**Positive**
- No EC2 ops burden — fits 4-person team's maintainability budget.
- Containers ⇒ portable to on-prem compose without code change (Portability).
- Per-second billing + Fargate Spot for non-critical workers fits cost ceiling.
- Native ALB integration, AZ failover handled by platform.

**Negative**
- Cold-start higher than EC2 (acceptable at 200 TPS with min-replica policy).
- No GPU/specialized instance flexibility (not needed here).
- Slightly pricier than EC2 at sustained load; mitigated by Fargate Spot for pollers.

## Alternatives Considered
| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Lambda | Fully managed, scale-to-zero | 15-min limit awkward for channel pollers; cold start hurts dashboard p99 | Polling workloads + interactive dashboard mix poorly |
| EKS | Most flexible, K8s ecosystem | Control-plane cost, ops complexity for team of 4 | Overkill at this scale; ADR-0005 deployment matrix doesn't need it |
| EC2 + Auto Scaling | Cheapest at sustained load | OS patching, AMI mgmt — maintainability hit | Team time more expensive than the Fargate premium |
