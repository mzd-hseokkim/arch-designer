---
name: diagram
description: Generate architecture diagrams from design.md. Logical views via D2 (SVG), deployment views via diagrams.py with AWS/GCP/Azure/K8s/on-prem icon sets (PNG).
user-invocable: true
argument-hint: "[project-name] [--target=aws|gcp|azure|k8s|onprem]"
allowed-tools: [Read, Write, Edit, Bash]
---

# diagram

Two renderers, one source of truth (`design.md`):

| View | Renderer | Format | Why |
|---|---|---|---|
| System Context | D2 | SVG | cloud-agnostic, embeddable, interactive |
| Container (logical) | D2 | SVG | same |
| Deployment (per target) | diagrams.py | PNG | real AWS/GCP/Azure/K8s/on-prem icons |

Multiple `--target` values → one deployment diagram per target, all derived from the same design.

## Inputs
- `.claude/arch-designer/<project>/design.md`

## Outputs
- `.claude/arch-designer/<project>/diagrams/context.d2` + `.svg`
- `.claude/arch-designer/<project>/diagrams/container.d2` + `.svg`
- `.claude/arch-designer/<project>/diagrams/deployment-<target>.py` + `.png`

## Render commands (reference)

D2:
```
docker run --rm -v "$PWD:/work" -w /work terrastruct/d2:latest \
  --layout=elk diagrams/context.d2 diagrams/context.svg
```

diagrams.py:
```
docker run --rm -v "$PWD:/work" -w /work gtramontina/diagrams:0.23.4 \
  diagrams/deployment-aws.py
```

## Dependencies
- Docker (only host requirement)
- `terrastruct/d2:latest`
- `gtramontina/diagrams:0.23.4`

## Conventions
- D2: layout `elk`, default theme. One `.d2` file per view.
- diagrams.py: `direction="LR"`, `Cluster` per logical zone, `Edge(style="dashed")` for async flows.
- Custom in-house components → `diagrams.custom.Custom` with PNG asset under `assets/`.

## diagrams.py import gotchas (v0.23.x)

LLM-friendly cheatsheet — first-render failures are usually from these. Verify with `python -c "from diagrams.<path> import <Class>"` before authoring if unsure.

| Symbol | Correct import path | Common wrong guess |
|---|---|---|
| `SQS` | `diagrams.aws.integration import SQS` | `SimpleQueueService` (doesn't exist as alias) |
| `MSK` (Kafka) | `diagrams.aws.analytics import ManagedStreamingForKafka as MSK` | `diagrams.aws.integration` |
| `Cognito` | `diagrams.aws.security import Cognito` | `diagrams.aws.identity` |
| `HPA` | `diagrams.k8s.clusterconfig import HPA` | `diagrams.k8s.others` |
| `Limits`, `Quota` | `diagrams.k8s.clusterconfig` | same |
| `Argocd` | `diagrams.onprem.gitops import Argocd` | `diagrams.onprem.cd` |
| `Istio` | `diagrams.onprem.network import Istio` | `diagrams.onprem.servicemesh` (non-existent) |
| `Keycloak`, `Dex` | `diagrams.onprem.identity` | `auth` |
| `Ceph`, `Minio` | `diagrams.onprem.storage` | `inmemory` |
| `Sagemaker` | `diagrams.aws.ml import Sagemaker` | `diagrams.aws.analytics` |

If an import fails at render time, the **first** fix is to check this table, then `ls /usr/local/lib/python3.11/site-packages/diagrams/<provider>/` inside the image. Do not invent submodule paths.

## Next
`/arch-designer:iac-gen <project>`
