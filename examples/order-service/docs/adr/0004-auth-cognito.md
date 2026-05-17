# ADR-0004: Authentication = Amazon Cognito User Pool

- **Status**: accepted
- **Date**: 2026-05-17
- **Deciders**: arch-designer (LLM-proposed, pending human review)

## Context
Seller (ID/PW + 2FA) and seller-employee RBAC (§3.6). Mobile clients require OAuth2/PKCE. K-ISMS audit logging (§3.6). Team capacity does not allow self-hosting an IdP (§3.7).

## Decision
**Amazon Cognito User Pool** for seller authentication. TOTP MFA enforced for seller-owner role, optional for employees. App clients: web (auth code + PKCE), mobile (PKCE). Group claims used for RBAC (`seller-owner`, `seller-employee`).

## Consequences
**Positive**
- Managed MFA, password policy, account recovery — zero custom code.
- Free tier covers 50K MAU; scenario has 10K DAU ⇒ well under.
- CloudTrail integration meets K-ISMS audit-log requirement.
- ALB / API Gateway native Cognito authorizer.

**Negative**
- Cognito UI is dated; custom hosted UI or fully custom screens required for UX parity with modern SaaS.
- Locked to AWS; on-prem DR cannot reuse Cognito — DR plan must accept read-only mode or pre-provisioned Keycloak shadow (deferred decision).

## Alternatives Considered
| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Keycloak self-hosted | Open source, portable to on-prem | Operational burden for 4-person team | Team-size constraint |
| Auth0 / Okta | Best UX, all features | Cost grows quickly; data residency unclear for KR | Budget + §3.6 dataResidency |
| Custom auth (Spring Security + bcrypt) | Full control | Build & maintain MFA, audit, password reset, etc. | Maintainability disaster |
