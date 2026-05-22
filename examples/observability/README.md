# Observability examples

This folder demonstrates Phase 17 runtime observability and operational intelligence with local-only fixtures. The examples do not call external services and do not change GovAI verdict semantics.

## Prerequisites

- Python **3.10+** on `PATH` as `python3`
- Repository root as current working directory for paths in the manifest and snapshot

## Files

| File | Purpose |
|------|---------|
| [sample-runtime-events.jsonl](sample-runtime-events.jsonl) | Runtime event stream matching [`../../observability/runtime-event-schema.json`](../../observability/runtime-event-schema.json) |
| [sample-dashboard-summary.json](sample-dashboard-summary.json) | Dashboard-ready summary keyed by metric IDs from [`../../observability/dashboard-metrics.json`](../../observability/dashboard-metrics.json) |
| [sample-incident-report.md](sample-incident-report.md) | Operator triage narrative linking incidents to audit traces |
| [sample-operational-snapshot.json](sample-operational-snapshot.json) | Canonical sample snapshot used by validators, scoring, and report generators |
| [run-observability-check.sh](run-observability-check.sh) | Runs `observability_check.py` with JSON to stdout |
| [run-operational-health-score.sh](run-operational-health-score.sh) | Runs `operational_health_score.py` against the sample snapshot |
| [run-operational-intelligence-report.sh](run-operational-intelligence-report.sh) | Generates the deterministic Markdown report on stdout |

## Audit Trace Mapping

Runtime events carry `run_id`, `tenant_id`, `policy_id`, and `audit_trace_id`. Operators use those fields to move from a dashboard alert to the corresponding GovAI audit export. The event stream intentionally omits prompts, completions, secrets, and raw customer payloads.

## Dashboard Consumption

Dashboards can aggregate `sample-runtime-events.jsonl` into the metric IDs in `sample-dashboard-summary.json`:

- `runtime_evaluations_total`
- `runtime_blocked_verdict_rate`
- `runtime_evaluation_latency_p95_ms`
- `audit_trace_correlated_events_total`
- `governance_incidents_total`

## Incident Triage

When an event has `event_name: govai.runtime.incident.detected`, classify it using [`../../observability/incident-taxonomy.json`](../../observability/incident-taxonomy.json), open the linked audit trace, and record operator action in the incident report.

## Quickstart

```bash
python3 scripts/observability_check.py
bash examples/observability/run-observability-check.sh
bash examples/observability/run-operational-health-score.sh
bash examples/observability/run-operational-intelligence-report.sh
```

Aggregate Makefile gate (chains everything plus the documentation `gate`):

```bash
make observability-check
```

## Notes

- The scripts only read the sample JSON; they do not make network calls and they do not mutate the repository.
- The shell drivers print one JSON object (or one Markdown bundle for the report generator) per run.
- For runtime event schema details see [`../../docs/observability/runtime-telemetry-contract.md`](../../docs/observability/runtime-telemetry-contract.md).
