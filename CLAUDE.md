# arch-designer — plugin conventions

이 repo에서 작업할 때 Claude가 따라야 할 규약. 일반 코딩 철학은 사용자 전역 CLAUDE.md에 있음 — 여기는 이 plugin 고유 룰만.

## 1. Skill authoring

- 새 skill = `skills/<name>/SKILL.md`. **본문은 instructions만**, 실행 코드/스크립트 금지.
- frontmatter 필수 필드: `name`, `description`, `user-invocable`, `argument-hint`, `allowed-tools`.
- skill 간 상태 전달 통로는 **단일 파일**: `.claude/arch-designer/<project>/context.json`. 다른 경로/포맷으로 우회 금지.
- `argument-hint`는 사용자가 입력할 인자만, 내부 옵션은 SKILL.md 본문에서 처리.

## 2. Decision tracing

- 모든 부수 결정은 design.md prose에 흡수. ADR은 **핵심 결정 ~5개만**.
- IaC의 모든 `resource` / `module` 블록에 `ADR-NNNN: <reason>` 한 줄 주석 — ADR 없으면 prose 결정 인용.
- ADR Alternatives 표는 "industry standard"/"best practice" 핑계 금지. **숫자, NFR 인용, 구체 근거**만.
- ADR 번호는 sequential, 4자리, 절대 재사용 금지. status 변경 시 새 ADR로 supersede.

## 3. Host dependencies

- **Docker만** 호스트 의존. Java/Python/Go/Terraform CLI는 컨테이너로 캡슐화.
- 새 도구 추가 시:
  - 해당 SKILL.md "Dependencies" 섹션 갱신
  - 루트 README.md "Dependencies" 표 갱신
  - 가능하면 이미지 태그 핀 (예: `hashicorp/terraform:1.9`, `terrastruct/d2:latest`는 latest 허용)

## 4. Examples maintenance

- SKILL.md 구조 변경 시 `examples/order-service/`도 함께 갱신해 회귀 가시화.
- 시나리오 추가 시 `examples/README.md` 표에 한 줄.
- examples 산출물은 **시뮬레이션 결과**임을 README에 명시 — 실제 slash command 결과와 구분.

## 5. Anti-patterns

- skill 본문에서 `bash`/`python` 실행 로직 작성 금지 — SKILL.md는 명세, 실행은 Claude가 도구 호출로.
- ADR 없는 상태에서 iac-gen 단계 진행 금지 (skill flow가 강제).
- `.claude/arch-designer/<project>/` 밖에 파이프라인 산출물 쓰지 않음.
- plugin.json `version` 무시 금지 — 사용자 facing 변경 시 항상 bump.

## 6. Validation gate

PR/커밋 전 최소 점검:
- 변경한 skill을 `examples/order-service/`에 적용했을 때 산출물이 합리적인지 mental check.
- README badges의 version과 plugin.json `version`이 일치하는지.
- 새로 추가한 Docker 이미지가 Linux/amd64에서 동작하는지 (Windows 호스트에서 `docker run --platform linux/amd64` 강제 가능).
