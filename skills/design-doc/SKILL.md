---
name: design-doc
description: Synthesize an arc42-lite design document and Architecture Decision Records (ADRs) from requirements.md + context.json. This skill makes the actual architectural decisions — anchor every choice to an NFR or FR.
user-invocable: true
argument-hint: "[project-name]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, WebSearch]
---

# design-doc

Second skill in `arch-designer`. Turns captured requirements into an opinionated design and a set of ADRs. This is where the LLM commits to choices — every choice must trace back to a stated FR or NFR.

## Inputs
- `.claude/arch-designer/<project>/requirements.md`
- `.claude/arch-designer/<project>/context.json`

## Outputs
- `.claude/arch-designer/<project>/design.md` — arc42-lite, 7 sections
- `.claude/arch-designer/<project>/docs/adr/NNNN-<slug>.md` — one file per major decision
- `.claude/arch-designer/<project>/context.json` — updated with `decisions: [...]` array (slug + status)

## Flow

### 1. Load and verify
- Read `context.json`. Abort if `nfr.performance`, `nfr.reliability`, `nfr.security`, or `targets` are missing — instruct user to rerun `gather-reqs`.
- Read `requirements.md`. Build a checklist of every FR use case and every NFR with a numeric value.

### 2. Identify decisions to make
Scan requirements and produce a **decision list** before writing anything. Typical decisions for a web service:

| Decision | Triggered by |
|---|---|
| Compute model (containers / serverless / VMs) | Performance, Maintainability, target |
| Sync vs event-driven boundaries | Reliability, peak TPS, latency target |
| Primary datastore (Aurora / RDS / DynamoDB / PostgreSQL on K8s) | Data model, RPO, scale |
| Caching strategy (in-process / Redis / CDN) | p99 latency, read pattern |
| Authn/Authz model (Cognito / Keycloak / Dex / Auth0) | Security, compliance, target |
| Network topology (public / private subnets / VPN / Zero Trust) | Security, compliance |
| Deployment topology (single-AZ / Multi-AZ / Multi-Region / Active-Active) | SLA, RPO/RTO, cost |
| Observability stack (CloudWatch / Prometheus+Grafana+Loki) | target, ops maturity |
| CI/CD (GitHub Actions / ArgoCD / CodePipeline) | target, deployment cadence |

Drop irrelevant rows. Add domain-specific rows when FRs warrant (e.g., search engine choice, ML model serving).

Cap ADRs at **~7**. If more come up, fold the smaller ones into design.md prose.

**Forced ADR candidates from constraints**: scan `context.json.constraints` for any item that names a *structural* property of the system (not a budget number, team size, or familiarity). Each one is an ADR candidate — the constraint goes verbatim in the ADR's Context, and Alternatives must explain why the constraint forbids them. Examples that should always become an ADR:

| Constraint shape | Why it forces an ADR |
|---|---|
| "domains > datastores: consolidate by coupling" | Datastore topology decision; alternatives differ |
| "company-standard: kubernetes" | Compute model decision is settled but its consequences (operator burden, mesh choice) need recording |
| "multi-region: KR+JP" | Topology decision with data-sovereignty and cost implications |
| "data-residency: per-country" | Replication and analytics-aggregation strategy |
| "channel-adapters: pluggable" | Modular extensibility pattern |

Constraints that are *values* ("budget < $3K", "team-size: 4") inform decisions but rarely warrant their own ADR — they appear as Context citations in other ADRs.

### 3. Write ADRs first, design.md second

Each ADR is independent and gets reused. design.md references them by number.

#### ADR template (`docs/adr/NNNN-<slug>.md`)
```markdown
# ADR-NNNN: <decision title>

- **Status**: accepted
- **Date**: 2026-05-17
- **Deciders**: arch-designer (LLM-proposed, pending human review)

## Context
<the FR/NFR pressure that forced this choice — quote specific numbers from requirements.md>

## Decision
<the single chosen option, stated as an imperative>

## Consequences
**Positive**
- <impact on specific NFR axes>

**Negative**
- <trade-off, cost, complexity>

## Alternatives Considered
| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| <alt 1> | … | … | … |
| <alt 2> | … | … | … |
```

Numbering: sequential, 4 digits, never reuse. Slug: kebab-case from decision title.

### 4. Write design.md (arc42-lite, 7 sections)

```markdown
# <Project Name> — Design Document

## 1. Introduction & Goals
<from requirements §1; restate top 3 quality goals with numbers>

## 2. Constraints
<technical, organizational, regulatory — pulled from requirements §3.6/§3.8 and context.json.constraints>

## 3. Solution Strategy
<3-5 bullets summarizing the architectural approach. Each bullet links to its ADR.>

## 4. Building Block View
<logical containers and their responsibilities — this section drives `diagram` skill's container.d2>

### 4.1 Level 1: System Context
<external actors and systems>

### 4.2 Level 2: Containers
<table of containers: name, technology, responsibility, ADR reference>

## 5. Runtime View
<2-4 key scenarios as numbered steps or sequence-style prose. Cover the highest-TPS and most failure-sensitive flows.>

## 6. Deployment View
<one subsection per target in context.json.targets>

### 6.1 AWS
<services chosen, network layout, AZ/Region strategy — drives diagrams.py deployment-aws.py>

### 6.2 On-Prem
<equivalent on-prem stack — drives deployment-onprem.py>

## 7. Architecture Decisions
| # | Decision | Status |
|---|---|---|
| [ADR-0001](docs/adr/0001-…) | … | accepted |
| [ADR-0002](docs/adr/0002-…) | … | accepted |
```

### 5. Update context.json
Append:
```json
"decisions": [
  { "id": "ADR-0001", "slug": "database-aurora-vs-rds", "status": "accepted" },
  { "id": "ADR-0002", "slug": "sync-vs-event-driven", "status": "accepted" }
]
```

`diagram` and `iac-gen` read this array to know which decisions are settled.

### 6. Surface uncertainty
At the end of the run, print to the user:
- Decisions made (list ADR titles)
- Assumptions that hardened into decisions (anything that was `inferred` in requirements but is now committed in an ADR)
- Open questions (decisions deferred — e.g., specific instance sizes, SLA tier of managed services)

Ask: "확정/수정할 부분이 있습니까?" Edit ADRs in place if the user changes their mind; bump ADR status to `superseded` and write a new one when reversing a prior decision.

## Anti-patterns (do NOT do)

- Don't write a decision without quoting the FR/NFR that forced it. If you can't, the decision doesn't belong in an ADR — push it to design.md prose.
- Don't list 15 alternatives per ADR. Pick the 2-3 that a working architect would actually consider.
- Don't recommend tech with hand-wavy "industry standard" justification. Be concrete: "Aurora chosen over RDS because RPO target is 5 min and Aurora's continuous backup meets it without operator action."
- Don't pre-decide things `iac-gen` should decide (specific instance types, exact CIDR blocks, IAM policy contents). Stay at the architectural layer.
- Don't skip the Deployment View per target. The whole point is target-portability.

## Next
`/arch-designer:diagram <project>`
