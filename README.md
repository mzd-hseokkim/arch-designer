# arch-designer

Claude Code plugin that takes free-form Functional/Non-Functional Requirements and produces a design document, architecture diagrams (D2), and Infrastructure-as-Code (Terraform / Kubernetes / docker-compose).

## Pipeline

```
/arch-designer:gather-reqs   →  requirements.md
/arch-designer:design-doc    →  design.md (arc42-lite)
/arch-designer:diagram       →  context.d2 / container.d2 (SVG)
                                + deployment-<target>.py (PNG, real cloud/on-prem icons)
/arch-designer:iac-gen       →  aws/*.tf | k8s/*.yaml | onprem/docker-compose.yaml
```

All artifacts land in `.claude/arch-designer/<project>/` in the current working directory.

## Status

v0.1.0 — Scaffolding + behavioural spec (SKILL.md per skill + iac-reviewer agent). Validated end-to-end against one scenario — see [`examples/order-service/`](./examples/order-service/) for the actual artifacts the pipeline produces (design doc, ADRs, diagrams, Terraform/compose, reviewer findings).

Next milestone: real slash-command install + invocation on a fresh project; multi-scenario validation.

## Install

### From GitHub (recommended)

In Claude Code:
```
/plugin marketplace add mzd-hseokkim/arch-designer
/plugin install arch-designer@arch-designer-marketplace
```

Or wire it in `~/.claude/settings.json`:
```json
{
  "extraKnownMarketplaces": {
    "arch-designer": {
      "source": { "source": "github", "repo": "mzd-hseokkim/arch-designer" }
    }
  }
}
```

### Local checkout (development)

```json
{
  "extraKnownMarketplaces": {
    "arch-designer-local": {
      "source": { "source": "directory", "path": "C:/path/to/arch-designer" }
    }
  }
}
```

Restart Claude Code after editing settings.

## Dependencies

Host requirement: **Docker only.** All toolchains run as containers.

- `terrastruct/d2` — logical-view rendering (SVG)
- `gtramontina/diagrams` — deployment-view rendering with AWS/GCP/Azure/K8s/on-prem icons (PNG)
- `hashicorp/terraform` — Terraform validation
- `alpine/helm`, `garethr/kubeval` — K8s validation
- `docker compose config` — compose validation
