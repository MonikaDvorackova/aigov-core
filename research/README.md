# GovAI research and academic publication artefacts

This directory holds **machine-readable** metadata for reproducible evaluation, citation, and replication studies of GovAI. The bundle is validated by `python3 scripts/validate_research_manifest.py` and aggregated by `python3 scripts/research_package_check.py` (see `make research-package-check`).

## Contents

| File | Purpose |
| --- | --- |
| [research-manifest.json](research-manifest.json) | Canonical index: artefact paths, documentation anchors, stable URNs, and version fields. |
| [benchmark-methodology.json](benchmark-methodology.json) | Benchmark scope, protocol steps, and referenced local benchmark assets (no network). |
| [reproducibility-checklist.json](reproducibility-checklist.json) | Replication and environment pinning guidance as structured checklist items. |
| [citation-metadata.json](citation-metadata.json) | Software and paper-style citation hooks aligned with repository `CITATION.cff`. |
| [experimental-design.json](experimental-design.json) | Pre-specified hypotheses, measures, and analysis boundaries for empirical studies. |
| [threats-to-validity.json](threats-to-validity.json) | Limitations and validity threats with cross-links to mitigations in documentation. |

## Narrative documentation

Canonical prose lives under **`docs/research/`** (benchmark methodology, reproducibility, experimental design, threats to validity, citation guide, publication strategy, open science).

## Examples

Worked examples and a shell driver: **`examples/research/`**.

## Non-goals

- These JSON files **do not** change compliance verdict semantics, Rust runtime enforcement, or database migrations.
- They **do not** replace peer review or legal certification.
