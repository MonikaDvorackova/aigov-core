# Research examples

## Experimental plan

See `sample-experimental-plan.json` for a structured example referenced by the research manifest.

## Research package check (existing)

```bash
bash examples/research/run-research-package-check.sh
```

## Microbenchmarks (audit-chain synthesis)

```bash
bash examples/research/run-microbenchmarks.sh
```

Or:

```bash
python3 scripts/microbenchmark_audit_engine.py --json
```

See `docs/research/microbenchmarks.md` and `docs/research/quantitative-feasibility.md`.

## Empirical evaluation (throughput, chain verification, export, storage, tenants, failures)

```bash
bash examples/research/run-empirical-evaluation.sh
```

Or:

```bash
export GOVAI_EMPIRICAL_QUICK=1
make empirical-evaluation-run empirical-evaluation-check
```

See `docs/research/empirical-evaluation.md`, `docs/research/benchmark-manifest.json`, and `examples/research/sample-benchmark-results.json` (illustrative JSON shape).
