## AI discovery (silent infra)

AI discovery is meant to run continuously (CI or local) and act as a **silent infrastructure layer**:
- It detects AI usage in your repository.
- It produces structured findings (detector + confidence + file paths).
- It can optionally submit a discovery event to the hosted backend for a `run_id`.
- The backend turns discovery signals into **compliance requirements** (visible via `govai compliance-summary`).

### Scan a repository

From the repo root:

```bash
cd python
python -m aigov_py.cli discovery scan --path ..
```

Text output (stderr) is useful for humans; JSON output (stdout) is useful for CI.

Disable history enrichment (faster, no `git` required):

```bash
cd python
python -m aigov_py.cli discovery scan --path .. --no-history
```

### Submit findings to the hosted backend

Submitting writes an `ai_discovery_reported` evidence event for the given `run_id`.
This is what makes the backend enforce discovery-driven requirements.

```bash
export GOVAI_AUDIT_BASE_URL="https://YOUR_GOVAI_AUDIT_SERVICE"
export GOVAI_API_KEY="YOUR_API_KEY"
export GOVAI_RUN_ID="550e8400-e29b-41d4-a716-446655440000"

cd python
python -m aigov_py.cli discovery scan --path .. --submit
```

You can also pass `--run-id` directly instead of using env vars.

### Check compliance impact

Once submitted, check compliance requirements and decision:

```bash
cd python
python -m aigov_py.cli compliance-summary --run-id "$GOVAI_RUN_ID"
python -m aigov_py.cli explain --run-id "$GOVAI_RUN_ID"
python -m aigov_py.cli check --run-id "$GOVAI_RUN_ID"
```

Discovery signals currently map to requirements like:
- `ai_discovery_completed` (always required)
- `model_registered` + `usage_policy_defined` (when OpenAI usage is detected)
- `evaluation_completed` (when local model / transformers usage is detected)
- `model_artifact_documented` (when model artifacts are detected)

