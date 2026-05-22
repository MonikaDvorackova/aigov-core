# Runtime observability and operational intelligence

This directory hosts the **Phase 17** observability layer for GovAI: a machine-readable manifest, deterministic validators, an offline scoring tool, an aggregated diagnostics check, and a Markdown report generator. The layer summarises **runtime health**, **readiness**, **evidence flow**, and **diagnostics** signals collected outside the audit service and turns them into operator-facing artefacts. It does **not** change the **VALID / INVALID / BLOCKED** verdict surface, billing, ledger, or database schema semantics — those remain governed by the hosted audit service and existing phases.

## Contents

| File | Purpose |
|------|---------|
| [observability-manifest.json](observability-manifest.json) | Canonical index of signals, score weights, probes, documents, and required checks |
| [runtime-telemetry-contract.md](runtime-telemetry-contract.md) | Runtime event names, fields, severity, correlation, and privacy contract |
| [event-taxonomy.md](event-taxonomy.md) | Event families and when operators should emit each event |
| [slo-and-sla-guidance.md](slo-and-sla-guidance.md) | Example runtime governance SLOs and SLA boundaries |
| [incident-response.md](incident-response.md) | Runtime governance incident classification and triage flow |
| [operational-dashboards.md](operational-dashboards.md) | Dashboard-ready metric guidance |
| [logging-guidance.md](logging-guidance.md) | Structured logging, redaction, and retention guidance |
| [runtime-health.md](runtime-health.md) | Runtime health signals captured per snapshot |
| [readiness-signals.md](readiness-signals.md) | Readiness booleans surfaced from operator probes |
| [evidence-flow-observability.md](evidence-flow-observability.md) | Evidence ingest and verdict-distribution observability |
| [diagnostic-snapshots.md](diagnostic-snapshots.md) | Operational snapshot schema and authoring guidance |
| [operational-risk.md](operational-risk.md) | Risk-level derivation and follow-up workflow |
| [telemetry-boundaries.md](telemetry-boundaries.md) | What this layer does **not** observe or modify |
| [operational-intelligence-report.md](operational-intelligence-report.md) | Markdown report generator usage notes |

## Executable checks

From the repository root:

```bash
make observability-manifest
make operational-snapshot
make observability
make operational-health-score
make operational-intelligence-report
make observability-check
```

JSON diagnostics:

```bash
python3 scripts/observability_check.py --json
python3 scripts/validate_observability_manifest.py --json
python3 scripts/validate_operational_snapshot.py --json
python3 scripts/operational_health_score.py --input examples/observability/sample-operational-snapshot.json
```

Deterministic Markdown report:

```bash
python3 scripts/generate_operational_intelligence_report.py --input examples/observability/sample-operational-snapshot.json
```

See also [`../../examples/observability/README.md`](../../examples/observability/README.md).

Machine-readable runtime event contracts start at [`../../observability/runtime-event-schema.json`](../../observability/runtime-event-schema.json).
