# Python SDK example

Minimal notes for calling the audit API from Python using the **in-repo** client.

## Install (from this repository)

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

## Sample snippet

```python
from govai.client import GovAIClient
import os

client = GovAIClient(
    os.environ["GOVAI_AUDIT_BASE_URL"],
    api_key=os.environ.get("GOVAI_API_KEY"),
    default_project=os.environ.get("GOVAI_PROJECT"),
)
summary = client.request_json("GET", "/compliance-summary", params={"run_id": os.environ["GOVAI_RUN_ID"]})
print(summary)
```

## Docs

See `docs/integrations/python-sdk.md` and `docs/cli-reference.md`.
