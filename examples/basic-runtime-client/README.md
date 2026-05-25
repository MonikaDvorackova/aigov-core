# Basic runtime client (curl)

Copy-pasteable smoke flow against the **`aigov_audit`** HTTP runtime (ledger-authoritative core).

## Prerequisites

- A running `aigov_audit` process (`make run-audit` from the repository root).
- `GOVAI_LEDGER_DIR`, `GOVAI_API_KEYS`, and `GOVAI_API_KEYS_JSON` configured on the server (see [docs/quickstart-runtime.md](../../docs/quickstart-runtime.md)).

## Tenant isolation

- Ledger tenant is resolved **only** from `Authorization: Bearer <api_key>` via `GOVAI_API_KEYS_JSON`.
- `X-GovAI-Project` is optional **metadata** (labels, metering hints) and **does not** select the ledger tenant.

## Run the smoke script

```bash
export GOVAI_AUDIT_BASE_URL="http://127.0.0.1:8088"
export GOVAI_API_KEY="<same secret as in GOVAI_API_KEYS>"
export GOVAI_RUN_ID="smoke-$(date +%s)"

./examples/basic-runtime-client/smoke-runtime.sh
```

The script calls, in order:

1. `POST /evidence`
2. `GET /compliance-summary/:run_id`
3. `GET /api/export/:run_id`
4. `GET /verify/:run_id`

With only a discovery event ingested, the compliance verdict is typically **BLOCKED** (missing lifecycle evidence). That is expected for a minimal smoke.

## Fixtures

- [`fixtures/discovery-event.json`](fixtures/discovery-event.json) — minimal ingest payload.
