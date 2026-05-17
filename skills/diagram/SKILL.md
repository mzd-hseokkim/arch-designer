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

## Next
`/arch-designer:iac-gen <project>`
