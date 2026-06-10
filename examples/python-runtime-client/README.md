# Python runtime client

Stdlib-only example against the **`aigov_audit`** core HTTP API (same routes as the curl smoke script).

## Prerequisites

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cd ..
```

Server env (separate terminal):

```bash
export GOVAI_LEDGER_DIR="$(pwd)/.govai-ledger"
mkdir -p "$GOVAI_LEDGER_DIR"
export GOVAI_API_KEYS="$GOVAI_API_KEY"
export GOVAI_API_KEYS_JSON="{\"$GOVAI_API_KEY\":\"local-dev\"}"
export AIGOV_ENVIRONMENT=dev
export AIGOV_POLICY_DIR="$(pwd)/rust"
make run-audit
```

## Run

```bash
export GOVAI_AUDIT_BASE_URL="http://127.0.0.1:8088"
export GOVAI_API_KEY="<server allowlist secret>"
export GOVAI_RUN_ID="py-smoke-$(date +%s)"

python3 examples/python-runtime-client/run_runtime_smoke.py
```

Optional metadata header (does **not** change ledger tenant):

```bash
export GOVAI_PROJECT="team-label-only"
```

## LangChain-style hook (optional)

The repository ships a stdlib adapter (no LangChain import). See [`langchain_tool_hook.py`](langchain_tool_hook.py) and `python/aigov_py/runtime/adapters/langchain.py`.

```bash
export GOVAI_EXAMPLE_EXECUTE=1
python3 examples/python-runtime-client/langchain_tool_hook.py
```
