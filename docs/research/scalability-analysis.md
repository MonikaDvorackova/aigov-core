# Scalability analysis

Multi-tenant benchmarks execute **sequential** tenant-scoped workloads for tenant counts **1, 10, 100** when `GOVAI_EMPIRICAL_QUICK=1`, and **1, 10, 100, 1000** in full mode, to quantify CPU-bound interleaving overheads as tenant cardinality grows. This models logical isolation (distinct `run_id` namespaces) rather than network-isolated processes.

Read `multi-tenant-benchmarks.json` for `baseline_relative_slowdown` and throughput.

## Related

- `docs/research/empirical-evaluation.md`
- `docs/multi-tenant/overview.md`
