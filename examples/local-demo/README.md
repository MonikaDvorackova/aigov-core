# Local demo (read-only)

This folder supports a **read-only** local check of the audit HTTP API (`/health`, `/ready`, `/status`). It does **not** submit evidence, does **not** use API keys, and does **not** mutate the ledger.

Formal contract (read-only vs **`make fail-closed-demo`**, exit codes, env vars): **[`CONTRACT.md`](CONTRACT.md)**.

## Prerequisites

- Audit service listening on **`127.0.0.1:8088`** by default (override with **`GOVAI_AUDIT_BASE_URL`**).
- Typical start: from repo root run **`docker compose up -d --build`** (see **`docs/project/local_development.md`**).

## Run the harness

From the **repository root**:

```bash
make local-demo
```

Equivalent:

```bash
python3 scripts/run_local_demo.py
```

## Run curl samples

```bash
make local-demo-curl
```

Or:

```bash
bash examples/local-demo/curl-health-ready.sh
```

## Expected behavior

- **`GET /health`** — HTTP **200** when the process is listening (liveness only).
- **`GET /ready`** — HTTP **200** when Postgres, migrations, and ledger checks succeed.
- **`GET /status`** — optional; non-200 responses are reported but do not fail the Python harness when `/health` and `/ready` are OK.

See **`expected-output.md`** for example Markdown-style summaries.

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Connection refused | Compose not running, wrong port, or wrong **`GOVAI_AUDIT_BASE_URL`**. |
| `/ready` not 200 | **`DATABASE_URL`** / Postgres not reachable from the audit container; migrations; ledger path permissions. |
| Slow first boot | Wait for DB healthcheck then re-run **`make local-demo`**. |

Canonical documentation remains under **`docs/`** in the repository root.
