# Load testing methodology

## Workload model

Ingestion uses payload sizes **1 KiB through 64 KiB** in full mode; quick mode exercises **1 KiB and 4 KiB** only to keep CI wall time bounded while still bracketing small structured events. Ingestion event counts are **1 000 and 10 000** when `GOVAI_EMPIRICAL_QUICK=1`, and **1 000, 10 000, and 100 000** otherwise. Hash-chain verification uses **1 000 and 10 000** events in quick mode and **1 000, 10 000, 100 000, and 1 000 000** in full mode.

## Execution environment

Record Python version, platform, and `GOVAI_EMPIRICAL_QUICK` in each JSON artefact. Re-run on a quiet machine for publication tables; CI uses quick mode for bounded runtime.

## Optional HTTP probe

When `GOVAI_BENCHMARK_HTTP=1` and credentials are present, ingestion benchmarks may append a single `POST /evidence` probe latency. Failure to connect does not fail the suite; the artefact records `http_probe.enabled=false`.

## Threats to validity

- **Interpreter bias:** Python timings bound Rust server throughput only indirectly.
- **Warmth:** No deliberate JVM-style warmup rounds; first iterations included in statistics.
- **Synthetic payloads:** May not match production event shapes or compression ratios.

## Related

- `docs/research/empirical-evaluation.md`
- `docs/research/statistical-methodology.md`
