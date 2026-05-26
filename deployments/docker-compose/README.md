# Docker Compose operator stack

Self-hosted **GovAI Core** (`aigov_audit`) with Postgres for SQL migrations. No commercial platform UI or entitlement services.

```bash
cd deployments/docker-compose
docker compose up --build -d
curl -sS http://127.0.0.1:8088/health
curl -sS http://127.0.0.1:8088/ready
```

Set `GOVAI_API_KEY=operator-dev-key` (must match `GOVAI_API_KEYS_JSON` in the compose file) for authenticated routes.

See [docs/runtime-operations.md](../../docs/runtime-operations.md) and [docs/backup-and-recovery.md](../../docs/backup-and-recovery.md).
