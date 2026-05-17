# On-Prem docker-compose — order-service (DR cold-standby)

Per ADR-0005 §6.2. Same container images as AWS deployment; managed services replaced with self-hosted equivalents.

## Prereqs
- Docker Engine ≥ 24, docker compose plugin ≥ 2.20
- TLS cert/key at `nginx/certs/server.{crt,key}` (self-signed OK for cold standby)
- Container images mirrored to your internal registry (`registry.internal/...`)
- Inbound 443/80 from VPN or whitelisted IPs only (PII per §3.6)

## Apply
```sh
cp .env.example .env  # fill secrets
docker compose pull
docker compose up -d
docker compose ps
```

Health check:
```sh
curl -k https://localhost/healthz
```

## What's NOT included
- Backup / restore of pg_data volume (use `pg_dump` cron or volume snapshot)
- Logical replication subscription from AWS Aurora (operator wires up post-bring-up)
- Keycloak realm config and user sync from Cognito (separate runbook)
- FCM credentials (mount Secret separately)
- TLS certificate provisioning (out of scope)

## Cutover from AWS
1. Stop AWS ECS services or block ingress at Route 53.
2. Catch up logical replication lag to 0.
3. Update DNS to point to on-prem Nginx.
4. Reverse cutover requires fresh dump from on-prem PG into Aurora.
