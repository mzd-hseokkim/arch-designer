# ADR-0003: Channel adapters as isolated event-driven workers

- **Status**: accepted
- **Date**: 2026-05-17
- **Deciders**: arch-designer (LLM-proposed, pending human review)

## Context
Three channels (네이버 스마트스토어, 쿠팡, 자사몰), each with different ingestion patterns (polling vs webhook) and different rate limits. NFR §3.5 fault tolerance: "단일 채널 API 장애가 다른 채널 처리에 영향 주지 않아야 함." Maintainability §3.7: "채널 어댑터는 플러그인 형태로 확장 가능."

## Decision
Each channel = independent ECS service ("channel adapter") that:
1. Pulls (or receives webhook for) raw orders.
2. Normalizes into a canonical `OrderEvent` schema.
3. Publishes to **Amazon SQS** (one queue per channel, plus one DLQ).

A single `order-ingest` worker fan-ins from the queues into the database. Adding a new channel = new adapter service + new queue; no changes to ingest worker.

## Consequences
**Positive**
- Per-channel failure isolation: adapter crash / API outage only stalls one queue.
- SQS message retention (14 days) covers extended outages of single channel.
- Plugin extensibility: new channel ships as a new repo/container, configuration-only change to the platform.
- DLQ + replay for poison messages.

**Negative**
- Eventual consistency between channel state and dashboard (seconds-to-minutes); acceptable for SMB use case.
- More services to operate (3+ adapters + ingest) vs a monolith ingester.

## Alternatives Considered
| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Single monolithic ingester | Simplest deploy | One bad channel takes down all ingestion; violates §3.5 fault tolerance | Hard rejection by NFR |
| Kafka (MSK) instead of SQS | Replay, ordering, multiple consumers | Operational overhead, MSK minimums blow budget at 200 TPS | Cost/complexity unjustified |
| Step Functions orchestration | Visual workflow, retries built-in | State machine model fits poorly with continuous polling | Wrong fit |
