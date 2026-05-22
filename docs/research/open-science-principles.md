# Open science principles

This repository encourages:

- **Transparent methods** — commands and manifests checked into `research/` and validated in CI-style gates.
- **Deterministic diagnostics** — stdlib validators emit stable JSON shapes for archiving alongside papers.
- **Clear scope boundaries** — benchmarks and interchange validators are not legal certifications.

## Practical norms

- Publish **scripts and pins**, not only high-level prose.
- Prefer **signed tags** for releases referenced in studies.
- Archive a **snapshot** (for example Zenodo) when the venue requires immutability beyond git history.

## Cross-links

- Reproducibility: [reproducibility.md](reproducibility.md)
- Makefile aggregation: `make academic-publication-check` from the repository root.
