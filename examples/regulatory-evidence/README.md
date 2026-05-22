# Regulatory evidence examples

This folder demonstrates **Phase 14** regulatory tooling: diagnostics, manifest validation, obligations validation, and deterministic Markdown export.

## Prerequisites

- Python **3.10+** on `PATH` as `python3`
- Repository root as current working directory for paths in manifests

## Scripts

| Script | Purpose |
|--------|---------|
| [run-regulatory-check.sh](run-regulatory-check.sh) | Runs `regulatory_evidence_check.py` with JSON to stdout |
| [run-regulatory-export.sh](run-regulatory-export.sh) | Prints deterministic Markdown export on stdout (redirect to capture) |

## Quickstart

```bash
bash examples/regulatory-evidence/run-regulatory-check.sh
bash examples/regulatory-evidence/run-regulatory-export.sh
```

Aggregate Makefile gate (includes `make gate`):

```bash
make regulatory-check
```
