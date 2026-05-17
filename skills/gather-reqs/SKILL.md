---
name: gather-reqs
description: Interview the user to capture Functional Requirements and Non-Functional Requirements (ISO/IEC 25010). Accepts a free-form description first, then asks targeted follow-ups only for gaps that block downstream architectural decisions.
user-invocable: true
argument-hint: "[project-name]"
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion]
---

# gather-reqs

First skill in the `arch-designer` pipeline. Captures what the service is supposed to do and the qualities it must exhibit. Output drives `design-doc`, `diagram`, and `iac-gen`.

## Inputs
- `$1` — project name (kebab-case). If missing, ask once.

## Outputs
- `.claude/arch-designer/<project>/requirements.md` — human-readable spec
- `.claude/arch-designer/<project>/context.json` — machine-readable downstream input

## Flow

### 1. Free-form intake
Open with a single, low-friction prompt:

> "이 서비스가 무엇이고, 누가 어떻게 쓰는지 자유롭게 설명해주세요. 길이/형식 무관. 이미 정해진 기술 스택이나 제약이 있으면 같이 적어주세요."

Read whatever the user writes. Do **not** ask anything yet.

### 2. Extract and bucket
Parse the free-form input into:

**Functional**
- Primary actors / personas
- Core use cases (verb-object pairs)
- External system integrations
- Key data entities
- Out-of-scope items (if stated)

**Non-functional — ISO/IEC 25010 8 axes**
1. **Functional Suitability** — completeness, correctness
2. **Performance Efficiency** — time behaviour, capacity (TPS, latency, payload size)
3. **Compatibility** — interoperability with existing systems, protocols
4. **Usability** — accessibility, supported clients/locales
5. **Reliability** — availability (SLA), fault tolerance, RPO/RTO
6. **Security** — authn/authz model, data classification, compliance (PCI/HIPAA/GDPR/K-ISMS)
7. **Maintainability** — team size, deployment cadence, modularity expectations
8. **Portability** — multi-cloud / on-prem requirement, vendor lock-in tolerance

Mark each item: **stated** (verbatim from user), **inferred** (reasonable from context), or **gap** (unknown).

### 3. Targeted follow-ups
Ask only for **gaps that block architectural decisions**. Prioritize in this order:

| Priority | Why it blocks design |
|---|---|
| Performance Efficiency (TPS, latency, concurrent users) | Sizing, async vs sync, caching strategy |
| Reliability (SLA, RPO/RTO) | Multi-AZ vs single-AZ, backup/replication topology |
| Security & Compliance | Network isolation, KMS, audit logging, region constraints |
| Portability (target environment) | AWS/GCP/Azure/K8s/on-prem — drives entire IaC output |
| Geographic / Data residency | Region selection, edge strategy |

Use `AskUserQuestion` in **clusters** (2-4 related questions per call), not one-by-one. Skip an axis entirely if the user already covered it. Cap total follow-up rounds at **3**.

Lower-priority axes (Usability, Maintainability, Compatibility) — make reasonable assumptions and surface them as `inferred` in the output rather than asking.

### 4. Confirm assumptions
Before writing files, show the user a concise list of **inferred** values and ask once: "다음 가정으로 진행할까요? 수정할 항목이 있으면 알려주세요."

### 5. Write outputs

#### `requirements.md` structure
```markdown
# <Project Name> — Requirements

## 1. Overview
<one-paragraph summary, derived from free-form intake>

## 2. Functional Requirements
### 2.1 Actors
### 2.2 Use Cases
### 2.3 External Integrations
### 2.4 Data Entities
### 2.5 Out of Scope

## 3. Non-Functional Requirements (ISO/IEC 25010)
### 3.1 Functional Suitability
### 3.2 Performance Efficiency
### 3.3 Compatibility
### 3.4 Usability
### 3.5 Reliability
### 3.6 Security
### 3.7 Maintainability
### 3.8 Portability

## 4. Assumptions
<list of inferred items the user did NOT explicitly state>

## 5. Open Questions
<things still unresolved — for human review>
```

Each NFR item: `**<metric>**: <value> _(stated|inferred)_`

#### `context.json` schema
```json
{
  "project": "order-service",
  "createdAt": "2026-05-17T12:00:00Z",
  "targets": ["aws", "onprem"],
  "primaryRegion": "ap-northeast-2",
  "nfr": {
    "performance": { "peakTps": 500, "p99LatencyMs": 200 },
    "reliability": { "slaPercent": 99.9, "rpoMinutes": 5, "rtoMinutes": 30 },
    "security": { "compliance": ["K-ISMS"], "dataClassification": "PII" },
    "portability": { "multiCloud": false, "vendorLockInTolerance": "medium" }
  },
  "scaleHints": { "users": "10K-100K", "growthHorizonMonths": 12 },
  "constraints": ["budget: under $5K/mo", "team-size: 4"]
}
```

Downstream skills read `context.json` first, `requirements.md` second.

## Anti-patterns (do NOT do)

- Don't ask a 20-question survey upfront — most users abandon.
- Don't invent numbers silently — anything not stated must be marked `inferred` and confirmed.
- Don't recommend a tech stack here — that's `design-doc`'s job.
- Don't ask about Usability/Maintainability/Compatibility unless the user opens the door; assume sensible defaults.

## Next
`/arch-designer:design-doc <project>`
