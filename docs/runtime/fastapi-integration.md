# FastAPI integration

FastAPI is **optional**. Adapter helpers live in [`python/aigov_py/runtime/adapters/fastapi.py`](../../python/aigov_py/runtime/adapters/fastapi.py) and import **`fastapi` only when you call them**, keeping plain imports of `aigov_py.runtime` lightweight.

## Dependency injection

Use [`make_client_dependency`](../../python/aigov_py/runtime/adapters/fastapi.py) with a factory that builds a [`RuntimeGovernanceClient`](../../python/aigov_py/runtime/client.py) (for example reading `GOVAI_AUDIT_BASE_URL`, `GOVAI_API_KEY`, and `GOVAI_PROJECT` from the environment).

```python
from fastapi import Depends, FastAPI

from aigov_py.runtime import RuntimeGovernanceClient
from aigov_py.runtime.adapters.fastapi import make_client_dependency

def client_factory() -> RuntimeGovernanceClient:
    ...

app = FastAPI()
dep = make_client_dependency(client_factory)

@app.get("/_/compliance/{run_id}")
def read_compliance(run_id: str, govai: RuntimeGovernanceClient = Depends(dep)):
    return govai.get_compliance_summary(run_id).raw
```

## App state pattern

[`install_client_on_app`](../../python/aigov_py/runtime/adapters/fastapi.py) and [`get_runtime_client_from_request`](../../python/aigov_py/runtime/adapters/fastapi.py) store a single shared client on `app.state` when you prefer that to per-request construction.

## Example

Runnable sample: [`../../examples/runtime-governance/fastapi-example.py`](../../examples/runtime-governance/fastapi-example.py) (requires `pip install 'aigov-py[server]'` from `python/`).

## Related

- [Python SDK](python-sdk.md)
- [Error handling](error-handling.md)
