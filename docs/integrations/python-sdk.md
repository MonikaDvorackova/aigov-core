# Python SDK usage and hardening

## Purpose

Document how engineers should use the **in-repo Python surfaces** (`govai` CLI, `python/govai/client.GovAIClient`, and `python/aigov_py` tooling) for reliable integration with the Rust audit service—timeouts, headers, errors, and exit codes—without changing runtime enforcement semantics.

## Integration overview

Python integration has two layers:

1. **`GovAIClient`** (`python/govai/client.py`) — session-based HTTP client for the audit API (`POST /evidence`, `GET /compliance-summary`, exports, health checks). Uses `requests`, bearer auth, optional `X-GovAI-Project` header (metadata; tenant selection remains server-side per operator configuration).
2. **`govai` CLI** (`python/aigov_py/cli.py`) — operator and CI commands including `govai check` with exit codes documented in `docs/cli-reference.md`.

Portable standards validation (`govai standards`, interchange JSON) is **orthogonal** to hosted verdicts: it proves structural conformance and digest stability, not ledger history.

## Implementation steps

1. **Install** — from the repo: `cd python && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`; from PyPI: pin `aigov-py` per `docs/cli-reference.md`.
2. **Configure** — set `GOVAI_AUDIT_BASE_URL`, `GOVAI_API_KEY`, and optionally `GOVAI_PROJECT` / `GOVAI_RUN_ID` for scripts.
3. **Post evidence** — use `GovAIClient.request_json("POST", "/evidence", json_body=...)` with payloads matching OpenAPI; handle `GovAIHTTPError` for 4xx/5xx.
4. **Gate promotions** — use `govai check` (or `get_compliance_summary` + explicit verdict handling) so CI fails closed on non-`VALID`.
5. **Hardening** — set explicit timeouts, retry only idempotent GETs, log correlation IDs if your wrapper adds them, and pin dependency versions in services.

## Validation

- `python3 scripts/developer_integrations_check.py`
- `make developer-integrations-check`
- Unit tests: see `python/tests/test_govai_sdk.py` for patterns; extend with mocks rather than hitting production.
- For interchange-only validation: `python3 scripts/validate_standard_conformance.py --json <file>`.

## Failure modes

- **Silent project mismatch** — `X-GovAI-Project` is metadata; wrong assumptions about tenancy cause confusion. Mitigation: read `docs/technical-documentation.md` and operator docs for tenant keys.
- **Timeout too low** — large evidence posts fail mid-flight. Mitigation: tune `timeout`, stream if you add streaming support in a fork.
- **Confusing exits in CI** — mixing CLI exit codes (`EX_BLOCKED` vs `EX_ERR`). Mitigation: map explicitly in shell scripts; see `examples/blocked_deployment.sh` for intentional BLOCKED demos.
- **Using interchange validators as legal proof** — standards checks validate shapes/digests, not regulatory outcomes. Mitigation: keep customer claims aligned with `docs/trust/trust-model.md`.
