## Golden path (local demo): audit service → artefacts → submit → verify → `VALID`

This is a **local, repository-oriented demo** of the CI contract shape (`govai-compliance-gate` after `submit-evidence-pack` + `verify-evidence-pack`).

If you are an **external customer onboarding to a hosted GovAI backend**, start here instead:

- `docs/customer-onboarding-10min.md` (canonical customer entrypoint)
- `docs/evidence-pack.md` (supported evidence pack commands + file shape)

A first-line **`VALID`** from `govai check` alone is **not** sufficient proof unless the ledger ingest and digest continuity steps completed successfully beforehand.

### Required components

- Running **GovAI audit HTTP API** (Rust `aigov_audit`) with DB + writable ledger (**`GET /ready` = HTTP 200**).
- **`govai` CLI** from this repo (`pip install -e "./python[dev]"` from the repository root) or an equivalent **`aigov-py`** pin.
- Environment for CLI:
  - **`GOVAI_AUDIT_BASE_URL`** — audit base URL (no trailing ambiguity; strip trailing slashes in your head when comparing).
  - **`GOVAI_API_KEY`** — bearer token accepted by the service (`GOVAI_API_KEYS_JSON` / `GOVAI_API_KEYS` mapping on the server), unless your dev server is explicitly configured to allow unauthenticated audit routes (**not** for staging/production).

### Exact working sequence (repository root)

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@127.0.0.1:5432/DATABASE'
export GOVAI_AUTO_MIGRATE=true
make audit_bg
```

Install the CLI (`python/` venv):

```bash
cd python && python -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e ".[dev]" && cd ..
```

Golden-path artefacts (**new `run_id` every invocation**):

```bash
export GOVAI_AUDIT_BASE_URL='http://127.0.0.1:8088'
export GOVAI_API_KEY='YOUR_LOCAL_OR_CI_KEY'
RUN_ID="$(govai demo-golden-path --output-dir artefacts --print-run-id 2>/dev/null)"
```

Ingest, verify digest/host continuity (same path + `RUN_ID`), then **`check`**:

```bash
govai submit-evidence-pack --path artefacts --run-id "$RUN_ID"
govai verify-evidence-pack --path artefacts --run-id "$RUN_ID"
govai check --run-id "$RUN_ID"
```

### Expected **`VALID`** output (stdout contract)

Immediately on stdout:

```text
VALID
```

Trailing **`GovAI summary`** block ends with **`verdict: VALID`**:

```text
GovAI summary
verdict: VALID
category: policy
reason_codes: []
next_action: Proceed with deployment.
```

Exit code **`0`** for `govai check` only when **`verdict === VALID`**.

### Failure modes (explicit)

| Symptom | Likely cause | Next action |
|--------|----------------|-------------|
| `doctor`/`curl` **`/health` OK but `/ready` not 200** | DB down, migrations not applied, ledger dir not writable | Fix `DATABASE_URL`, `GOVAI_AUTO_MIGRATE` vs operator migration discipline, **`GOVAI_LEDGER_DIR`** mounts/permissions |
| **`401` / missing API key** | Wrong or unset `GOVAI_API_KEY` vs server mapping | Align CLI key with `GOVAI_API_KEYS_JSON` (or disable keys only in deliberate local dev) |
| **`404` RUN_NOT_FOUND** on check | Wrong tenant / key; run id never ingested under this ledger | Submit again with the correct key; verify `RUN_ID` |
| **`verify-evidence-pack` ≠ 0 before check** | Skipped submit, corrupted `artefacts/<run_id>.json`, or tampered digest | Regenerate artefacts; rerun **submit → verify** before asserting `VALID` |

### Operational notes

- **`--require-export`** on `verify-evidence-pack` adds a hard dependency on **`GET /api/export/:run_id`**. Omit it unless your environment guarantees export parity (hosted gate may enable it explicitly).
- **Determinism:** bundle content is stable for a fixed `run_id`; **`demo-golden-path` generates a new UUID** except when tests patch `uuid.uuid4`. Stable digest hashing is **`portable_evidence_digest_v1`** (`python/aigov_py/portable_evidence_digest.py`; mirrors Rust canonical JSON rules).
- **API keys in logs:** reuse **`export GOVAI_API_KEY='…'`**; use **`govai demo-golden-path --show-api-key`** only when you consciously want the literal secret in regenerated command text.
