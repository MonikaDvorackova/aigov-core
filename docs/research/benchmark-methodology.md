# Benchmark methodology

GovAI ships **local, deterministic, stdlib-only** benchmark metadata under `benchmarks/` (see [`../../benchmarks/README.md`](../../benchmarks/README.md)). This document explains how to design and report studies that use those assets **without** overstating what they measure.

## What the benchmarks are

The auditability failure catalogue names scenarios (missing evidence, digest breaks, isolation expectations, and similar) and exercises them through a **Python stdlib runner**. Outputs describe **expected governance signals** for teaching and regression — they are **not** a second implementation of the hosted verdict engine.

## Evaluation protocol (high level)

1. **Pin the environment** — record git commit, Python version, and relevant environment variables (for example `GOVAI_MODE` when matching CI diagnostics).
2. **Run the catalogue** — execute `python3 benchmarks/auditability-failures/run_benchmark.py` (or the Makefile aggregation that includes it, such as `make oss-ecosystem-check`).
3. **Capture artefacts** — retain stdout/stderr and any emitted JSON for independent verification.

## Metrics and statistical rigor

- **Coverage** — count of scenarios exercised versus the catalogue size (descriptive, not inferential).
- **Regression stability** — repeated runs at the same commit should yield the same pass/fail pattern for deterministic scenarios.
- **Inferential statistics** — only appropriate when the study design defines a population, sampling frame, and estimand; the default catalogue is a **conformance harness**, not a sampled user population.

## Cross-links

- Reproducibility: [reproducibility.md](reproducibility.md)
- Threats to validity: [threats-to-validity.md](threats-to-validity.md)
- Machine-readable protocol: [`../../research/benchmark-methodology.json`](../../research/benchmark-methodology.json)
