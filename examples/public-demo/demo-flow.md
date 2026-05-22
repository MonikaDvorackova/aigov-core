# Public demo flow

Two tracks: **narrative-only** (always available) and **live local** (requires Docker and the audit service).

## Track 1 — Narrative-only (no services)

1. Open [sample-governance-scenario.md](sample-governance-scenario.md).
2. Walk through events A→G in order, pausing at each **`BLOCKED`** explanation.
3. Close with the **compliance gate** and **evidence pack** bullets from [README.md](README.md).

**Expected outcome:** audience understands **`run_id` discipline**, **`VALID` / `INVALID` / `BLOCKED`**, and why digest binding matters—even without curl output.

## Track 2 — Live local read-only (Docker)

**Prerequisites:** `docker compose up -d --build` from repo root; service on **`127.0.0.1:8088`** (or set `GOVAI_AUDIT_BASE_URL`).

From repository root:

```bash
make local-demo
```

**Expected output (high level):**

- Harness exits **0** when `/health` and `/ready` return **200** with expected JSON bodies.
- Non-200 on `/status` may be reported as advisory depending on harness rules—see **[`examples/local-demo/README.md`](../local-demo/README.md)**.

Optional curl samples:

```bash
make local-demo-curl
```

## Track 3 — Hosted pilot commands (secrets required)

Only after operator provisions **`GOVAI_AUDIT_BASE_URL`** and **`GOVAI_API_KEY`**.

```bash
python -m pip install "aigov-py==0.2.1"
export GOVAI_AUDIT_BASE_URL="https://your-audit-endpoint.example"
export GOVAI_API_KEY="***"
export GOVAI_RUN_ID="$(python3 -c "import uuid; print(uuid.uuid4())")"
export GOVAI_DEMO_RUN_ID="$GOVAI_RUN_ID"
govai run demo-deterministic
govai check --run-id "$GOVAI_RUN_ID"
```

**Expected behaviour:**

- Initially **`verdict: BLOCKED`** with explanatory `missing_evidence` and/or `blocked_reasons`.
- After the demo completes evidence for the same `run_id`, **`verdict: VALID`** on `GET /compliance-summary`.

Authoritative reference: **[`docs/customer-onboarding-10min.md`](../../docs/customer-onboarding-10min.md)**.

## Compliance gate narrative (for presenter)

1. State that **`.github/workflows/compliance.yml`** in this repository models the **strict** path.
2. Show inputs: `run_id`, `base_url`, `api_key`, `artifacts_path`.
3. Emphasize default **`require_export`** behaviour on the composite action when discussing enterprise audit expectations.

## Evidence pack narrative (for presenter)

1. Evidence events land in append-only order; invalid transitions are rejected.
2. Digest manifest in CI is compared to hosted **`GET /bundle-hash`** during verify.
3. Export JSON is the archival artefact for humans and tools.

## Related

- [Public launch demo script](../../docs/launch/demo-script.md)
- [GitHub Action reference](../../docs/github-action.md)
