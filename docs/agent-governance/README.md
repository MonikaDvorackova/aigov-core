# Agent governance, delegation, and multi-agent control

Phase 22 adds **offline governance tooling** for autonomous and multi-agent systems: a machine-readable **manifest**, a **delegation snapshot** format, **validators**, deterministic **scoring**, aggregated **diagnostics**, and a **Markdown report generator**. The tooling is stdlib-only, does not call hosted GovAI APIs, and does not change billing, ledger semantics, database schemas, or runtime enforcement.

## Canonical artefacts

| Artefact | Path |
| --- | --- |
| Governance manifest | [`agent-governance-manifest.json`](agent-governance-manifest.json) |
| Sample delegation snapshot | [`../../examples/agent-governance/sample-agent-delegation-snapshot.json`](../../examples/agent-governance/sample-agent-delegation-snapshot.json) |

## Scripts (repository root)

| Script | Role |
| --- | --- |
| `scripts/validate_agent_governance_manifest.py` | Validates manifest schema and that referenced paths exist. |
| `scripts/validate_agent_delegation_snapshot.py` | Validates delegation snapshot payloads. |
| `scripts/agent_governance_score.py` | Emits deterministic JSON scores, `risk_level`, `findings`, and `recommendations`. |
| `scripts/agent_governance_check.py` | Aggregates manifest, snapshot, score, Makefile wiring, docs, and example drivers. |
| `scripts/generate_agent_governance_report.py` | Emits deterministic Markdown for a single snapshot. |

## Makefile

From the repository root:

```bash
make agent-governance
make agent-governance-manifest
make agent-delegation-snapshot
make agent-governance-score
make agent-governance-report
make agent-governance-check
```

`make agent-governance-check` runs the targets above and **`make gate`** (required headings in `docs/reports/*.md`).

## Further reading

- [Delegation policies](delegation-policies.md)
- [Approval chains](approval-chains.md)
- [Multi-agent orchestration](multi-agent-orchestration.md)
- [Override governance](override-governance.md)
- [Agent accountability](agent-accountability.md)
- [Delegation risk management](delegation-risk-management.md)
- [Report generator notes](agent-governance-report.md)

## Non-claims

Snapshots and reports are **operator-supplied observational summaries**. They are not legal certifications and do not replace hosted audit verdicts or policy enforcement.
