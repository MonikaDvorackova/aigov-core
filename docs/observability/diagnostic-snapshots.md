# Diagnostic snapshots

Operational snapshots are deterministic JSON objects describing a point-in-time view of audit service runtime, readiness, evidence flow, and operator diagnostics. They are inputs for **offline scoring** ([`scripts/operational_health_score.py`](../../scripts/operational_health_score.py)) and the **operational intelligence report** ([`scripts/generate_operational_intelligence_report.py`](../../scripts/generate_operational_intelligence_report.py)).

A canonical sample lives at [`examples/observability/sample-operational-snapshot.json`](../../examples/observability/sample-operational-snapshot.json).

## Top-level fields

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | non-negative integer | Currently `1`. |
| `snapshot_id` | string | Operator-assigned stable identifier. |
| `captured_at` | string | ISO-8601 instant in UTC. |
| `environment` | string | Free-form label such as `staging` or `prod`. |
| `window_minutes` | positive integer | Duration of the observation window. |
| `runtime_health` | object | See [runtime-health.md](runtime-health.md). |
| `readiness` | object | See [readiness-signals.md](readiness-signals.md). |
| `evidence_flow` | object | See [evidence-flow-observability.md](evidence-flow-observability.md). |
| `diagnostics` | object | Operator-run diagnostic checks; see below. |

## Diagnostics object

```jsonc
{
  "summary": "Operator-friendly sentence (>= 24 chars).",
  "failure_count": 0,
  "warning_count": 0,
  "checks": [
    {"name": "audit_ready_probe", "ok": true, "detail": "GET /ready returned 200 within budget"}
  ]
}
```

The validator enforces:

- `failure_count` matches the number of `ok: false` entries in `checks`.
- Each `check` has `name`, `ok`, and `detail`.

## Authoring guidance

- Snapshots should be **fully deterministic**: avoid embedding wall-clock-only fields that change between runs of the same probe.
- Do **not** embed personally identifiable information (PII) or evidence payloads inside snapshots; they are bounded by [telemetry-boundaries.md](telemetry-boundaries.md).
- Each snapshot is **standalone**; the scoring tool does not maintain state between runs.

## Validators

```bash
python3 scripts/validate_operational_snapshot.py --input examples/observability/sample-operational-snapshot.json --json
make operational-snapshot
```
