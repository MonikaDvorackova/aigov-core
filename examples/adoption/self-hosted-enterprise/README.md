# Adoption kit: self-hosted enterprise (Docker Compose)

**Purpose:** Provide a **minimal, runnable** Compose layout to bring up **Postgres + GovAI audit API** for evaluation labs, using the same service shape as the root repository quickstart. Use this when you want a **concrete** self-hosted path without starting from an empty `docker-compose.yml`.

## Prerequisites

- Docker Compose v2.
- This **monorepo** cloned (the Compose `build.context` references `../../../rust` from this directory).
- No cloud secrets required for a local lab; use **dev-only** keys from `.env.example`.

## Quickstart

From this directory (`examples/adoption/self-hosted-enterprise/`):

```bash
cp .env.example .env
# Edit .env — set GOVAI_API_KEYS to a non-default value for anything beyond localhost.
docker compose -f docker-compose.example.yml up -d --build
```

Wait for readiness:

```bash
curl -fsS http://127.0.0.1:8088/ready
```

## Expected output

- `GET /ready` returns HTTP **200** when Postgres, migrations, and ledger checks succeed.
- `GET /health` returns `{"ok":true}` (liveness; see README troubleshooting for semantics).

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Build context error | Run from this path so `../../../rust` resolves to the repo `rust/` directory; or edit `context` to your checkout. |
| Port 5432 or 8088 in use | Stop conflicting services or change published ports in the compose file. |
| `ready` never succeeds | `docker compose logs govai-audit` — usually DB URL or migrations. See `docs/operator-runbook.md`. |
| Weak default password | **Never** use `postgres/postgres` outside a disposable VM; rotate for shared labs. |

## Scope limitations

- **Not** a production security baseline — add TLS, secrets management, backups, and network policy per `docs/security/secure-deployment-checklist.md`.
- Does **not** change **billing**, **tenant isolation**, **verdict semantics**, or **evidence digest** behaviour; it only orchestrates containers.
- **Stripe** and other hosted integrations are **out of scope** for this minimal file; see `docs/billing.md` if enabled in your environment.

## Related

- `docs/hosted-backend-deployment.md` · `docs/examples/enterprise-deployment.md` · `examples/reference/enterprise-deployment/README.md` · `docs/adoption/reference-implementations.md`
