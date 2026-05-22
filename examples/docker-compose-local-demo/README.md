# GovAI Docker Compose local demo

This directory documents the **same** root-level Docker Compose developer path used across the repository. The **authoritative** Compose file for the quick local stack is at the **repository root**: **`docker-compose.yml`**.

## One-command stack (repository root)

```bash
docker compose up -d --build
```

Wait until the audit service is ready:

```bash
curl -fsS http://127.0.0.1:8088/ready
```

The root compose file sets **`GOVAI_API_KEYS`** so the bearer **`test-key`** is accepted for authenticated routes (see root `docker-compose.yml`).

## Fail-closed BLOCKED demo (copy-paste)

Install the CLI from **`python/`** (venv at **`python/.venv`**):

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
cd ..
```

From the **repository root**, with Compose still running:

```bash
export GOVAI_AUDIT_BASE_URL=http://127.0.0.1:8088
export GOVAI_API_KEY=test-key
bash examples/blocked_deployment.sh
```

Same contract via the Python wrapper (JSON on stdout):

```bash
export GOVAI_AUDIT_BASE_URL=http://127.0.0.1:8088
export GOVAI_API_KEY=test-key
make fail-closed-demo
```

**Contract:** `govai check` must exit with code **3** (BLOCKED). The example script exits **0** only after confirming exit code **3** — see stderr for `blocked_deployment_example: OK`.

## Cleanup

```bash
docker compose down
```

## Operational notes

- **`GET /health`** — liveness only.
- **`GET /ready`** — operational readiness (Postgres, migrations, ledger expectations).
- Production deployments require durable ledger configuration and explicit operator settings; this demo uses convenience defaults.

## Submodule compose file

The **`docker-compose.yml`** in this directory is optional or experimental; prefer the **root** **`docker-compose.yml`** unless you know you need the copy here.
