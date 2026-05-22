# Operational intelligence report

[`scripts/generate_operational_intelligence_report.py`](../../scripts/generate_operational_intelligence_report.py) emits a deterministic Markdown report from a validated operational snapshot. The report bundles snapshot metadata, sub-scores, signal values, diagnostic checks, and findings into a single document suitable for offline review.

## Usage

Default sample:

```bash
python3 scripts/generate_operational_intelligence_report.py \
  --input examples/observability/sample-operational-snapshot.json
```

Custom snapshot, custom manifest, redirect to file:

```bash
python3 scripts/generate_operational_intelligence_report.py \
  --input path/to/snapshot.json \
  --manifest docs/observability/observability-manifest.json \
  --out reports/operational-intelligence.md
```

Makefile target (smoke-checks the generator):

```bash
make operational-intelligence-report
```

## Report structure

1. **Snapshot metadata** — `snapshot_id`, `captured_at`, `environment`, `window_minutes`, `schema_version`.
2. **Scores** — `health_score`, sub-scores, `risk_level`, `ok`, and the active `weights` from the manifest.
3. **Runtime health** — per-signal values.
4. **Readiness** — per-signal booleans.
5. **Evidence flow** — latency, success rate, submissions, decision distribution.
6. **Diagnostics** — failure/warning counts, operator summary, and a sorted list of recorded checks.
7. **Findings** — sorted findings produced by the scoring tool.
8. **Report metadata** — paths to the snapshot and manifest used.

## Determinism

The report is **content-addressed friendly**: identical inputs produce byte-identical output. Sorted keys, trimmed trailing whitespace, and an explicit final newline keep digests stable across runs.

## Non-claims

- The Markdown report is **not** a conformity statement, SLA report, or regulator-facing submission.
- It must not be used as a substitute for an authoritative audit export (`GET /api/export/:run_id`).
