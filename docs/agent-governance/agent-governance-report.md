# Agent governance report generator

`scripts/generate_agent_governance_report.py` turns one **delegation snapshot** into a **deterministic Markdown** bundle suitable for tickets, CAB packs, or internal wikis.

## Inputs

- `--input` — snapshot path relative to repository root (default: `examples/agent-governance/sample-agent-delegation-snapshot.json`).
- `--manifest` — governance manifest path (default: `docs/agent-governance/agent-governance-manifest.json`), used for score weights.

## Output shape

Sections appear in a stable order: snapshot metadata, governance scores (including weights when present), delegation, approval chain, override governance, auditability, findings, recommendations, and report metadata paths.

## Determinism

Lists inside Markdown (delegates, scopes, findings, recommendations) are **sorted lexicographically** so repeated runs with the same inputs yield byte-identical output.

## CI

The OSS workflow writes `.oss-ci-out/agent-governance-report.md` for artifact retention alongside JSON diagnostics.
