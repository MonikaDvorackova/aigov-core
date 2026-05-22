# Agent governance examples

This folder demonstrates **Phase 22** agent governance tooling: a sample delegation snapshot and shell drivers for diagnostics, manifest and snapshot validation, scoring, and the deterministic Markdown report generator.

## Prerequisites

- Python **3.10+** on `PATH` as `python3`
- Run commands from the **repository root** so relative paths resolve

## Files

| File | Purpose |
| --- | --- |
| [sample-agent-delegation-snapshot.json](sample-agent-delegation-snapshot.json) | Canonical sample snapshot for validators, scoring, and reports |
| [run-agent-governance-check.sh](run-agent-governance-check.sh) | Runs `agent_governance_check.py --json` |
| [run-agent-governance-score.sh](run-agent-governance-score.sh) | Runs `agent_governance_score.py` against the sample snapshot |
| [run-agent-governance-report.sh](run-agent-governance-report.sh) | Prints the deterministic Markdown report on stdout |

## Quickstart

```bash
bash examples/agent-governance/run-agent-governance-check.sh
bash examples/agent-governance/run-agent-governance-score.sh
bash examples/agent-governance/run-agent-governance-report.sh
```

Aggregate Makefile gate:

```bash
make agent-governance-check
```

## Notes

- Scripts are read-only against the sample JSON; no network calls and no repository mutations.
- Schema and operator guides live under [`../../docs/agent-governance/`](../../docs/agent-governance/).
