# GovAI public benchmarks (documentation and metadata)

This directory holds **local, deterministic, stdlib-only** benchmark metadata for teaching and regression of **auditability expectations**. Benchmarks here **do not** invoke the Rust audit service, do not mutate databases, and do not change compliance verdict semantics in production.

## Suites

| Suite | Path | Purpose |
| --- | --- | --- |
| Auditability failure catalogue | [auditability-failures](auditability-failures/README.md) | Named scenarios for missing evidence, approvals, digest breaks, isolation issues, etc. |

## Running checks

```bash
python benchmarks/auditability-failures/run_benchmark.py
# or via Makefile aggregation:
make oss-ecosystem-check
```

## Non-goals

- No leaderboard hosting, no external APIs, no GPU workloads.
- Scenario JSON describes **expected governance signals** for education; it is not a second implementation of the product verdict engine.
