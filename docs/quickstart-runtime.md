# GovAI Core audit runtime quickstart

Run the open-source **`aigov_audit`** binary: append evidence to a tenant-scoped ledger, read a ledger-authoritative compliance verdict, export an audit bundle, and verify the hash chain.

This guide uses **GovAI** terminology only. It does not start a hosted SaaS stack, background polling loop, or platform dashboard.

## What you need

| Requirement | Notes |
|-------------|--------|
| Rust toolchain | Build `aigov_audit` |
| Writable ledger directory | `GOVAI_LEDGER_DIR` |
| API key allowlist + tenant map | `GOVAI_API_KEYS` and `GOVAI_API_KEYS_JSON` |
| Policy files | `AIGOV_POLICY_DIR` pointing at `rust/` (ships `policy.dev.json`) |

PostgreSQL is **optional** for core ledger routes. It is only required when you enable DB-issued API keys or want `GET /ready` to check migrations.

## 1) Generate an API key and tenant mapping

```bash
export GOVAI_API_KEY="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
export GOVAI_LEDGER_DIR="$(pwd)/.govai-ledger"
mkdir -p "$GOVAI_LEDGER_DIR"

# Server-side (both are required when GOVAI_API_KEYS is set):
export GOVAI_API_KEYS="$GOVAI_API_KEY"
export GOVAI_API_KEYS_JSON="{\"$GOVAI_API_KEY\":\"local-dev\"}"
export AIGOV_ENVIRONMENT=dev
export AIGOV_POLICY_DIR="$(pwd)/rust"
```

**Tenant isolation:** the ledger tenant is **`local-dev`** because that is the value in `GOVAI_API_KEYS_JSON` for your bearer secret.  

**Not tenant isolation:** `X-GovAI-Project` is optional metadata (project label, usage attribution) only.

## 2) Start the runtime

```bash
make run-audit
```

Default bind: `http://127.0.0.1:8088` (`AIGOV_BIND` overrides).

In another terminal:

```bash
export GOVAI_AUDIT_BASE_URL="http://127.0.0.1:8088"
export GOVAI_API_KEY="<same value as above>"
curl -sS "$GOVAI_AUDIT_BASE_URL/health"
curl -sS "$GOVAI_AUDIT_BASE_URL/status"
```

`GET /ready` performs **non-mutating** dependency checks (no ledger appends).

## 3) Smoke the core route sequence

### curl (basic client)

```bash
export GOVAI_RUN_ID="quickstart-$(date +%s)"
chmod +x examples/basic-runtime-client/smoke-runtime.sh
./examples/basic-runtime-client/smoke-runtime.sh
```

Calls, in order:

1. `POST /evidence`
2. `GET /compliance-summary/:run_id`
3. `GET /api/export/:run_id`
4. `GET /verify/:run_id`

With a single discovery event, the verdict is usually **BLOCKED** (missing required lifecycle evidence). That is normal for a minimal smoke.

**Offline signed bundle verification** (no running server): [`signed-audit-export-verifier.md`](signed-audit-export-verifier.md) and `examples/signed-audit-export-bundle/demo.valid.zip`.

### Python (stdlib SDK)

```bash
cd python && python3 -m venv .venv && source .venv/bin/activate && pip install -e . && cd ..
python3 examples/python-runtime-client/run_runtime_smoke.py
```

Optional LangChain-style hook (existing adapter, dry-run by default):

```bash
export GOVAI_EXAMPLE_EXECUTE=1
python3 examples/python-runtime-client/langchain_tool_hook.py
```

## 4) Reach VALID (full lifecycle)

Append the governance lifecycle events for your `run_id` (data registration, training, evaluation, risk review, human approval, promotion). The integration test golden path in `rust/tests/runtime_core_integration.rs` is the reference ordering.

Then:

```bash
curl -sS -H "Authorization: Bearer $GOVAI_API_KEY" \
  "$GOVAI_AUDIT_BASE_URL/compliance-summary/$GOVAI_RUN_ID"
```

Expect `"verdict": "VALID"` when promotion state is `promoted` and required evidence is satisfied.

## Related docs

- [runtime-api-contract.md](runtime-api-contract.md) — mounted routes and auth rules
- [../api/govai-http-v1.openapi.yaml](../api/govai-http-v1.openapi.yaml) — full HTTP contract (platform routes labeled `platform-only`)
- [../examples/basic-runtime-client/README.md](../examples/basic-runtime-client/README.md)
- [../examples/python-runtime-client/README.md](../examples/python-runtime-client/README.md)
