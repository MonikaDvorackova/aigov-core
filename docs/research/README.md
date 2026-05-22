# Research and academic publication

This section supports **reproducible**, **citable**, and **publication-ready** use of GovAI in academic and industrial research.

## Where to start

| Topic | Document |
| --- | --- |
| Benchmark design and statistical framing | [benchmark-methodology.md](benchmark-methodology.md) |
| Replication, environment pins, and artefact retention | [reproducibility.md](reproducibility.md) |
| Hypotheses, measures, and analysis boundaries | [experimental-design.md](experimental-design.md) |
| Validity threats and limitations | [threats-to-validity.md](threats-to-validity.md) |
| Citing software and documentation | [citation-guide.md](citation-guide.md) |
| Venues, positioning, and disclosure norms | [publication-strategy.md](publication-strategy.md) |
| Open science practices aligned with this repository | [open-science-principles.md](open-science-principles.md) |

## Research support and operational evidence

Executable artefacts for manuscript- and enterprise-facing **operational evidence** (feasibility framing, synthetic microbenchmarks, structured threat sample, legal positioning, privacy patterns, provider cooperation, scalability). This package is **not** legal advice and does not certify regulatory compliance.

| Topic | Document |
| --- | --- |
| Quantitative feasibility (analytical model) | [quantitative-feasibility.md](quantitative-feasibility.md) |
| Microbenchmark methodology | [microbenchmarks.md](microbenchmarks.md) |
| Empirical benchmarking and load testing (measured hot paths) | [empirical-evaluation.md](empirical-evaluation.md), [benchmark-manifest.json](benchmark-manifest.json), [load-testing-methodology.md](load-testing-methodology.md) |
| Machine-readable manifest (paths + bundles) | [research-support-manifest.json](research-support-manifest.json) |

```bash
make manuscript-evidence-check
make empirical-evaluation-run empirical-evaluation-check
python3 scripts/research_support_check.py --json
```

## Machine-readable bundle

- **Index:** [`../../research/research-manifest.json`](../../research/research-manifest.json)
- **Human summary:** [`../../research/README.md`](../../research/README.md)

## Validation

```bash
python3 scripts/validate_research_manifest.py --json
python3 scripts/research_package_check.py --json
make research-package-check
make academic-publication-check
make manuscript-evidence-check
```

## Examples

See [`../../examples/research/README.md`](../../examples/research/README.md) for a sample experimental plan JSON and a shell driver.
