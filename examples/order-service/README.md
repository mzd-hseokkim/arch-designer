# order-service — Example Output

End-to-end artifacts for a Korean SMB multi-channel order management SaaS. Produced by running the full `arch-designer` pipeline against the scenario in [§ Scenario](#scenario).

## Scenario

> 주문 관리 SaaS. 한국 중소 셀러들이 쓸 거고, 자사몰/네이버 스마트스토어/쿠팡에서 들어오는 주문을 한 화면에서 본다. 웹 대시보드 + 셀러용 모바일 앱. 일 활성 사용자 1만 명 정도 예상, 피크는 점심/저녁. 결제는 직접 안 받고 외부 PG 호출만. 한국 리전 필수. 예산은 월 3000달러 안쪽. 팀은 4명, AWS 익숙. 일단 AWS로 가고 백업/DR은 온프렘 같이 검토.

That single paragraph is the only input to `gather-reqs`. Everything below is derived.

## File tree

```
order-service/
├── requirements.md                       # ISO/IEC 25010 8 axes, stated vs inferred
├── context.json                          # machine-readable state shared across skills
├── design.md                             # arc42-lite, 7 sections
├── docs/adr/
│   ├── 0001-compute-ecs-fargate.md
│   ├── 0002-database-aurora-serverless-v2.md
│   ├── 0003-channel-adapters-event-driven.md
│   ├── 0004-auth-cognito.md
│   └── 0005-deployment-multi-az-single-region.md
├── diagrams/
│   ├── context.{d2,svg}                  # D2 — system context
│   ├── container.{d2,svg}                # D2 — containers
│   ├── deployment-aws.{py,png}           # diagrams.py — AWS layout
│   └── deployment-onprem.{py,png}        # diagrams.py — on-prem DR
└── iac/
    ├── aws/                              # Terraform: VPC, ECS, Aurora, Cognito, SQS, ALB
    └── onprem/                           # docker-compose: PG, Redis, RabbitMQ, Keycloak, Nginx
```

## Diagrams

### System Context (D2)
![Context](diagrams/context.svg)

### Container View (D2)
![Container](diagrams/container.svg)

### AWS Deployment (diagrams.py)
![AWS Deployment](diagrams/out-deployment-aws.png)

### On-Prem DR Deployment (diagrams.py)
![On-Prem Deployment](diagrams/out-deployment-onprem.png)

## Architecture decisions

| # | Decision | Triggered by |
|---|---|---|
| [ADR-0001](docs/adr/0001-compute-ecs-fargate.md) | Compute = ECS Fargate | Performance + Maintainability + on-prem portability |
| [ADR-0002](docs/adr/0002-database-aurora-serverless-v2.md) | DB = Aurora PostgreSQL Serverless v2 | RPO 5min, spiky workload, K-ISMS |
| [ADR-0003](docs/adr/0003-channel-adapters-event-driven.md) | Channel adapters = isolated SQS workers | Fault isolation NFR + plugin extensibility |
| [ADR-0004](docs/adr/0004-auth-cognito.md) | Authn = Amazon Cognito | MFA + RBAC, team size |
| [ADR-0005](docs/adr/0005-deployment-multi-az-single-region.md) | Topology = Multi-AZ, single region | SLA 99.9% within $3K/mo budget |

Each ADR follows the Context / Decision / Consequences / Alternatives template. Every alternative table cites a concrete reason for rejection (no "industry standard" hand-waving).

## NFR coverage

`requirements.md` covers all 8 ISO/IEC 25010 axes with explicit `stated` / `inferred` tags. The user's free-form input addressed ~5 axes; the other 3 are `inferred` and surfaced in `## 4. Assumptions` for confirmation. NFR numeric values flow into `context.json.nfr` and drive downstream choices (e.g. RPO 5min → continuous backup → Aurora over RDS).

## IaC validation (iac-reviewer dry-run)

| Validator | Result |
|---|---|
| `terraform fmt -check -recursive` | pass (after 1 auto-fix) |
| `terraform init -backend=false` | pass — 5 modules resolved |
| `terraform validate` | pass |
| `docker compose config -q` | pass |

Findings surfaced for human attention:
- ALB needs ACM cert wired (deliberately commented in `main.tf`)
- `single_nat_gateway = true` is a cost trade-off — override for prod
- 5 ECS services beyond `api-gateway-svc` are the same pattern; stubbed with a NOTE rather than duplicated (avoid drift)
- See full report in commit history / `iac-reviewer` output

Estimated AWS monthly cost at the scenario's scale: **~$700** (vs $3000 ceiling).

## Caveats

- This output was produced by an LLM following the SKILL.md instructions in this repo. It is **not** the result of a real `/arch-designer:gather-reqs` invocation yet — the plugin install + slash-command flow is the next milestone.
- The Korean-language source paragraph drives mixed-language output (Korean prose with English technical terms). The plugin doesn't force one language; it follows the input.
- "Example" ≠ "production-ready." Treat these artifacts as a strong starting draft that a working architect would refine.
