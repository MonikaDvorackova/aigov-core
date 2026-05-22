# Reproducibility and replication

Reproducibility means another researcher can **obtain the same results** given the same inputs and environment. Replication means repeating the study design on **new data** or **new deployments** to test stability of conclusions.

## Environment pins

Minimum recommended pins:

- **Git commit** or signed release tag.
- **Python minor version** and whether a virtual environment was used.
- **Commands** copied verbatim from this repository (avoid paraphrasing shell steps).

## Artefact retention

For peer review, retain:

- Validator stdout (`python3 scripts/validate_research_manifest.py --json`, `python3 scripts/research_package_check.py --json`).
- Benchmark runner logs from `benchmarks/auditability-failures/run_benchmark.py` when they are part of the evidence chain.

## Replication vs product claims

Local benchmarks and documentation validators prove **repository state** and **structured artefacts**. Claims about **production** behaviour, **legal compliance**, or **tenant-specific** controls require operator evidence (logs, policies, approvals) beyond this package.

## Cross-links

- Checklist JSON: [`../../research/reproducibility-checklist.json`](../../research/reproducibility-checklist.json)
- Open science alignment: [open-science-principles.md](open-science-principles.md)
