---
name: iac-gen
description: Generate Infrastructure-as-Code for each target in context.json (Terraform for AWS/GCP/Azure, Helm chart for K8s, docker-compose for on-prem). Every resource must trace to an ADR decision or design.md building block.
user-invocable: true
argument-hint: "[project-name] [--target=aws|gcp|azure|k8s|onprem|all]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# iac-gen

Final skill in `arch-designer`. Materializes the design into runnable IaC, one tree per target. Validates with `iac-reviewer` subagent before reporting done.

## Inputs
- `.claude/arch-designer/<project>/design.md`
- `.claude/arch-designer/<project>/docs/adr/*.md`
- `.claude/arch-designer/<project>/context.json`

## Outputs (per target)

```
.claude/arch-designer/<project>/iac/
├── aws/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   ├── modules/        # only if a hand-written module is justified
│   └── README.md       # how to apply, what's NOT included (secrets, state backend)
├── k8s/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values.<env>.yaml
│   ├── templates/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingress.yaml
│   │   ├── configmap.yaml
│   │   └── _helpers.tpl
│   └── README.md
└── onprem/
    ├── docker-compose.yaml
    ├── .env.example
    ├── nginx/nginx.conf
    └── README.md
```

## Flow

### 1. Load and gate
- Require `context.json.decisions` to be non-empty. If empty → instruct user to rerun `design-doc`.
- Read all ADRs into memory. Build a map: `service-in-design` → `ADR(s)-that-justify-it`.
- Default target: every value in `context.json.targets`. Override with `--target=...`.

### 2. Per-target generation

#### AWS (Terraform)
- **Provider**: `hashicorp/aws ~> 5.0`. Pin in `versions.tf`.
- **Module strategy**: prefer `terraform-aws-modules/*/aws` (vpc, rds-aurora, eks, alb, s3-bucket, msk-kafka). Hand-write only when a module doesn't exist or adds more friction than it removes.
- **Resource → ADR comment**: every `resource` / `module` block gets a single-line comment referencing the ADR that justifies it.
  ```hcl
  # ADR-0001: Aurora chosen over RDS for 5-min RPO
  module "db" { source = "terraform-aws-modules/rds-aurora/aws" ... }
  ```
- **Variables, not literals**: region, environment, instance sizes, AZ count → `variables.tf` with sensible defaults. Never inline secrets or account IDs.
- **State backend**: write `backend.tf.example` (not `backend.tf`). User configures their own S3+DynamoDB.

#### Kubernetes (Helm chart)
- Generate as a chart (not raw YAML) — version-controllable, env overlays via `values.<env>.yaml`.
- One `Deployment` + `Service` + optional `Ingress` per container in design.md §4.2.
- `values.yaml` exposes: image tag, replicas, resources (requests/limits), env vars, ingress host.
- Use `_helpers.tpl` for name/label conventions. Standard labels: `app.kubernetes.io/{name,instance,version,managed-by}`.
- Optional: `HorizontalPodAutoscaler` only if ADR for autoscaling exists.
- ConfigMap for non-secret config; document Secret strategy in README (External Secrets / Sealed Secrets — don't generate raw Secret YAML with values).

#### On-prem (docker-compose)
- `docker-compose.yaml` v3.8+, one service per container from design.md §4.2.
- All tunables via `.env` (image tags, ports, volume paths). Provide `.env.example`.
- Named volumes for stateful services. Healthchecks for every long-running service.
- Reverse proxy: Nginx config in `nginx/nginx.conf` if design.md specifies an edge/gateway.
- No `latest` image tags — pin versions.

#### GCP / Azure
- Same Terraform pattern as AWS. Provider: `hashicorp/google` or `hashicorp/azurerm`. Module ecosystem thinner — more hand-written resources expected.

### 3. README per target
Each target's README answers:
- **Prereqs** — required CLI versions, cloud credentials, kube context
- **Apply** — exact commands (`terraform init && plan && apply`, `helm install ...`, `docker compose up`)
- **What's NOT included** — secrets, state backend config, DNS records, real ACM cert ARNs, IAM users (separated by security boundary)
- **Cost ballpark** — rough monthly estimate at the scale stated in `context.json.scaleHints` (AWS only)

### 4. Validate (invoke iac-reviewer)
After all files are written, invoke the `iac-reviewer` subagent on the generated tree. It runs:

| Target | Validators |
|---|---|
| Terraform | `terraform fmt -check`, `terraform init -backend=false`, `terraform validate`, `tflint` (if available) |
| Helm | `helm lint`, `helm template` + `kubeval` / `kube-linter` |
| compose | `docker compose -f docker-compose.yaml config` |

All run as Docker containers (no host installs). Reviewer returns structured findings; this skill fixes mechanical issues (formatting, missing required args) automatically and surfaces design-level findings to the user.

### 4b. Post-generation hygiene

After validators run, the IaC tree contains transient artifacts (most notably `.terraform/` from `terraform init` — hundreds of MB of provider plugins + module clones). Leaving these in the user's working tree pollutes commits.

Write a `.gitignore` at the **project root** (`.claude/arch-designer/<project>/.gitignore`) covering:

```
# Terraform
**/.terraform/
*.tfstate
*.tfstate.*
*.tfplan
crash.log
crash.*.log
# Backend config carries account-specific values
**/backend.tf

# Local secrets — never commit
**/.env
!**/.env.example

# Helm
**/charts/*.tgz

# OS / editor
.DS_Store
Thumbs.db
```

If `.gitignore` already exists, **merge missing entries** rather than overwriting.

Heads-up to surface in the final report (§5): the user's **outer** working directory (where they invoked Claude Code) may also pick up `.claude/settings.json` from Claude Code's session — that file is Claude Code's, not this plugin's, but the user likely wants it gitignored too. Recommend (don't auto-add) a single line `.claude/settings.local.json` in the outer repo's `.gitignore` if one exists.

### 5. Report
Print:
- Generated files (count per target)
- Validation results (pass/fail per validator)
- Anything flagged as needing human attention (secrets handling, state backend, cert/DNS, IAM)
- ADR coverage report: ADRs with no IaC manifestation (could be process decisions like "use ArgoCD" — fine, but flag)

## Anti-patterns (do NOT do)

- **No hallucinated module versions.** Pin only versions you have reason to trust; default to the latest known stable from the official registry.
- **No real values for secrets, account IDs, certificate ARNs, IPs.** Use variables with `EXAMPLE_` prefix or empty defaults + `description`.
- **No "kitchen sink"** — only generate resources that map to a building block in design.md or a decision in an ADR. If a resource has no anchor, it doesn't belong.
- **No copy-pasted boilerplate across targets** that drifts. If AWS and on-prem both need Nginx config, generate from one template, not two.
- **No inline IAM JSON policies more than ~10 lines.** Reference `aws_iam_policy_document` data sources or external JSON files.
- **Don't run `terraform apply` or `kubectl apply` or `docker compose up` from the skill.** Generate + validate only. Apply is the user's call.
- **No `"PLACEHOLDER"` / `"TODO"` strings in fields that pass syntax check but break at apply.** Specifically: ARNs, IDs, image tags, hostnames, CIDRs. If the value can't be known at generation time, either (a) declare a `variable` with `description` and **no default** (forces user to supply), or (b) comment out the entire block and add a `NOTE:` explaining the dependency. Never both compile and lie.
- **Don't double-manage what a module already manages.** If `terraform-aws-modules/rds-aurora` is configured with `manage_master_user_password = true`, do NOT also write a separate `aws_secretsmanager_secret`. Cross-check every hand-written resource against the modules in use.
- **Don't emit unwired half-features.** Example: an ALB with only `http_redirect` to port 443 but no HTTPS listener creates a redirect loop at apply. If the dependency (ACM cert) is external, comment out the listener block and document in README — never leave a known-broken configuration that compiles.
- **Don't drop services on one target that exist on another.** If design.md §6 lists 6 services on AWS and 6 on on-prem, both IaC trees must show 6. Stubs/notes are fine; silent omission isn't.

## Next
Pipeline complete. Optional follow-ups (not separate skills, just suggestions in the final report):
- `/arch-designer:diagram <project> --refresh` if design changed
- Human review of ADRs before applying
