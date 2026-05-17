# arch-designer

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.1-orange.svg)](.claude-plugin/plugin.json)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-7c3aed.svg)](https://docs.claude.com/en/docs/claude-code/plugins)

자유 서술 형태의 기능/비기능 요구사항을 받아 **설계 문서 → 아키텍처 다이어그램 → Infrastructure-as-Code**까지 일관되게 만들어주는 Claude Code 플러그인.

## What it does

서비스 한 문단 설명을 입력으로:

1. **요구사항 정리** — ISO/IEC 25010 8축으로 구조화, 추정값과 명시값 구분
2. **설계 문서 + ADR** — arc42-lite 7섹션, 핵심 결정 ~5개를 별도 ADR로 추적
3. **다이어그램** — D2(논리 뷰, SVG) + diagrams.py(실제 클라우드/온프렘 아이콘, PNG)
4. **IaC** — Terraform(AWS/GCP/Azure) · Helm(K8s) · docker-compose(온프렘), 모든 리소스에 ADR 주석 앵커
5. **검증** — `iac-reviewer` 서브에이전트가 fmt/lint/validate + ADR 커버리지 + target 간 대칭성 점검

각 단계가 다음 단계의 입력이 되고, 요구사항이 바뀌면 모든 산출물이 같이 갱신됩니다.

## Why

다이어그램 한 장 예쁘게 그리는 건 사람이 Figma/Excalidraw로 그리는 게 더 빠릅니다. 이 플러그인의 가치는 거기가 아니라:

- **결정의 일관성** — FR/NFR → 설계 결정 → 다이어그램 → IaC가 한 모델에서 파생
- **결정의 추적성** — ADR이 NFR을 인용하고, IaC가 ADR을 인용 (`# ADR-0001: ...` 주석)
- **변경 대응** — 요구사항 한 줄 바뀌면 어떤 결정이 영향받는지 추적 가능
- **개인 편향 회피** — Alternatives 표가 "industry standard" 핑계 대신 구체 근거 강제

## Pipeline

```
/arch-designer:gather-reqs <project>   →  requirements.md + context.json
/arch-designer:design-doc  <project>   →  design.md + docs/adr/NNNN-*.md
/arch-designer:diagram     <project>   →  diagrams/{context,container}.{d2,svg}
                                          + diagrams/deployment-<target>.{py,png}
/arch-designer:iac-gen     <project>   →  iac/{aws,k8s,onprem}/...
                                          (auto-invokes iac-reviewer)
```

모든 산출물은 작업 디렉토리의 `.claude/arch-designer/<project>/` 아래에 누적. 단계 간 상태 공유는 `context.json` 단일 파일.

## Usage walkthrough

새 프로젝트 디렉토리에서:

```text
$ claude

> /arch-designer:gather-reqs order-service

이 서비스가 무엇이고, 누가 어떻게 쓰는지 자유롭게 설명해주세요.
길이/형식 무관.

> 한국 SMB 셀러용 주문 관리 SaaS. 네이버 스마트스토어/쿠팡/자사몰
> 주문을 한 화면에서. 일 DAU 1만, AWS, 예산 월 3000달러, 팀 4명.

(자유 서술 파싱 + ISO/IEC 25010 8축 분류)

다음 갭이 설계 결정을 막습니다. 함께 알려주세요:
  - peak TPS / p99 latency 목표는?
  - SLA / RPO / RTO 목표는?
  - 컴플라이언스 요건은? (K-ISMS, PCI 등)

> [답변]

▸ 작성 완료
  .claude/arch-designer/order-service/requirements.md
  .claude/arch-designer/order-service/context.json
  
다음: /arch-designer:design-doc order-service

> /arch-designer:design-doc order-service

(결정 후보 식별 → ADR 5개 작성 → arc42-lite design.md 작성)

▸ 작성 완료
  design.md
  docs/adr/0001-compute-ecs-fargate.md
  docs/adr/0002-database-aurora-serverless-v2.md
  docs/adr/0003-channel-adapters-event-driven.md
  docs/adr/0004-auth-cognito.md
  docs/adr/0005-deployment-multi-az-single-region.md
  
확정/수정할 부분이 있습니까?

> 좋아, 다음으로 가자

> /arch-designer:diagram order-service

(Docker로 D2 + diagrams.py 렌더)

▸ 생성
  diagrams/context.svg
  diagrams/container.svg
  diagrams/deployment-aws.png
  diagrams/deployment-onprem.png

> /arch-designer:iac-gen order-service

(Terraform AWS + docker-compose 온프렘 생성 → iac-reviewer 자동 실행)

▸ 검증 결과
  terraform fmt:     pass (1 auto-fix)
  terraform validate: pass
  docker compose config: pass
  
  MECHANICAL: 0
  DESIGN: 6 (사람 검토 필요 — ALB ACM 미연결, NAT single-AZ 등)
  
  ADR 커버리지: 5/5
```

실제 산출물 예시는 [`examples/order-service/`](./examples/order-service/), [`examples/dispatch-hub/`](./examples/dispatch-hub/) 참조.

## Skills & agent

| Component | Role | Spec |
|---|---|---|
| `gather-reqs` | 자유 서술 + 갭 인터뷰 → requirements.md / context.json | [SKILL.md](skills/gather-reqs/SKILL.md) |
| `design-doc` | 결정 식별 → ADR → arc42-lite design.md | [SKILL.md](skills/design-doc/SKILL.md) |
| `diagram` | D2(논리) + diagrams.py(배포) 렌더 | [SKILL.md](skills/diagram/SKILL.md) |
| `iac-gen` | Terraform/Helm/compose 생성, iac-reviewer 호출 | [SKILL.md](skills/iac-gen/SKILL.md) |
| `iac-reviewer` | fmt/lint/validate + ADR 커버리지 + 대칭성 + lie-detector | [agent.md](agents/iac-reviewer.md) |

## Examples

| Example | Scenario | Targets | What it exercises |
|---|---|---|---|
| [`order-service`](examples/order-service/) | 한국 SMB 다채널 주문 관리 SaaS | AWS + 온프렘 DR | ECS Fargate, SQS per-channel, Aurora Serverless v2, Cognito MFA. **전 파이프라인 + 검증된 IaC** |
| [`dispatch-hub`](examples/dispatch-hub/) | B2B 라스트마일 배송 (KR+JP) | AWS + K8s (EKS) | MSK Kafka, Karpenter, **9 도메인 → 4 데이터스토어 통합**, per-country active-active, in-cluster ML |

## Install

### From GitHub (recommended)

Claude Code 안에서:
```
/plugin marketplace add mzd-hseokkim/arch-designer
/plugin install arch-designer@arch-designer-marketplace
```

또는 `~/.claude/settings.json`:
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
      "source": { "source": "directory", "path": "/path/to/arch-designer" }
    }
  }
}
```

설정 변경 후 Claude Code 재시작.

## Dependencies

호스트 요구사항: **Docker** 하나. 나머지는 전부 컨테이너로 실행.

| Container image | 용도 |
|---|---|
| `terrastruct/d2:latest` | 논리 뷰 렌더링 (SVG) |
| `gtramontina/diagrams:0.23.4` | 배포 뷰 렌더링 (AWS/GCP/Azure/K8s/온프렘 아이콘, PNG) |
| `hashicorp/terraform:1.9` | Terraform fmt/init/validate |
| `ghcr.io/terraform-linters/tflint`, `aquasec/tfsec` | TF lint / 보안 스캔 |
| `alpine/helm:3.16`, `garethr/kubeval`, `stackrox/kube-linter` | K8s 검증 |
| Docker CLI | `docker compose config` |

## Project layout

```
arch-designer/
├── .claude-plugin/
│   ├── plugin.json              # manifest
│   └── marketplace.json         # marketplace metadata
├── skills/
│   ├── gather-reqs/SKILL.md
│   ├── design-doc/SKILL.md
│   ├── diagram/SKILL.md
│   └── iac-gen/SKILL.md
├── agents/
│   └── iac-reviewer.md
├── examples/
│   ├── README.md
│   ├── order-service/           # full pipeline
│   └── dispatch-hub/            # through diagrams (IaC skipped)
├── CLAUDE.md                    # plugin conventions for contributors
├── LICENSE
└── README.md
```

## Conventions (TL;DR)

- 스킬 본문 = instructions만. 실행 코드 금지.
- 결정 ≤ 7개를 ADR로. 나머지는 design.md prose.
- 모든 IaC 리소스에 `# ADR-NNNN: <reason>` 주석.
- 의존성은 컨테이너로만. 호스트 설치 강요 금지.
- target 간 비대칭(AWS만 6 서비스, 온프렘은 1) → reviewer가 잡음.

전체 컨벤션: [CLAUDE.md](CLAUDE.md).

## Status

v0.1.1 — 4 스킬 + 1 에이전트 + 2 시나리오 end-to-end 검증 완료 (LLM dry-run). 실 슬래시 명령 호출은 다음 마일스톤.

## License

[MIT](LICENSE)
