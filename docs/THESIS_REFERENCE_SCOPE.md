# Thesis reference — scope note (v0.1)

This repository supports **academic work** on governance-by-design for ML: lifecycle decisions made **machine-checkable** through append-only evidence, explicit identifiers, and policy-gated promotion. The scholarly claim is about **engineering mechanisms**, not legal compliance from the repository alone.

> **Disclaimer:** The codebase is a **research prototype** with **no legal guarantee**; EU AI Act mentions are illustrative, not authoritative interpretation.

## What the thesis may reference (faithfully)

- **Architecture**: Python training and evidence emission versus Rust append-only governance API and ledger, as in [ARCHITECTURE.md](../ARCHITECTURE.md).
- **Evidence model**: hash-chained JSONL, `POST /evidence` ingest, bundle document (`aigov.bundle.v1` via `GET /bundle`), compliance summary (`aigov.compliance_summary.v2` via `GET /compliance-summary`); identifiers and projection contract in [strong-core-contract-note.md](strong-core-contract-note.md).
- **Illustrative regulation mapping**: the [EU AI Act](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689) **Articles 9–13** only as **non-exhaustive** framing for risk, data, documentation, logging, and transparency **mechanisms**—aligned with [technical-documentation.md](technical-documentation.md) where it describes the same mapping, not as an exhaustive legal reading.
- **Reproducibility**: exact commands and representative outputs in [DEMO_FLOW.md](../DEMO_FLOW.md).
- **Optional reference path**: [docs/demo/golden-run/README.md](demo/golden-run/README.md) documents where pinned snapshots would live if added; v0.1 relies on the live `make` flow for reproduction.

## Boundaries (avoid over-claiming)

- The codebase is a **v0.1 reference PoC** ([OPEN_SOURCE_SCOPE.md](../OPEN_SOURCE_SCOPE.md)); it is not certification-ready software.
- **EU AI Act** mentions in docs or sample payloads are **illustrative**; they are not legal advice.
- Dashboard and Supabase paths are **optional product surfaces**; the regulation-agnostic core is the Rust ledger + bundle/summary contracts.

## Confirmation (maintainers / author)

Add a one-line factual citation block here when the thesis is public (title, year, institution) if needed for attribution. No placeholder is assumed correct until provided.
