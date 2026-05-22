# Statistical methodology

For repeated latency samples, the harness reports:

- sample `count`
- `mean_ms`, `median_ms`, `stdev_ms` (population standard deviation)
- `min_ms`, `max_ms`
- `p50_ms`, `p95_ms`, `p99_ms` via linear interpolation on the **sorted** empirical distribution

These are **descriptive statistics** over repeated executions on a single host. They do **not** constitute hypothesis tests, confidence intervals over independent deployments, or Bayesian posterior estimates.

## Related

- `docs/research/load-testing-methodology.md`
- `scripts/empirical_benchmark_lib.py`
