# Review and acceptance criteria

Maintainers evaluate registry and marketplace submissions on **safety**, **clarity**, **validator compatibility**, and **operational honesty**.

## Required checks (automation)

- `python3 scripts/registry_check.py`
- `python3 scripts/validate_policy_pack.py` for each pack directory touched
- `python3 scripts/validate_marketplace_manifest.py marketplace/manifest.json`
- `make gate` (audit report headings) when reports change
- `python3 scripts/validate_docs_links.py --strict` when documentation links change

## Human criteria

1. **Claims proportionality** — prose matches what validators can actually prove.
2. **Interchange alignment** — `govai_policy_module_interchange` hints reference real [`docs/standards/registry.md`](../standards/registry.md) versions.
3. **Evidence codes** — requirement `code` and `required_evidence` entries are internally consistent and documented (even briefly) in the pack README.
4. **Duplication** — if a pack overlaps an existing one, authors should justify why both should exist or propose consolidation.

## Acceptance outcomes

- **Approve** — merge with catalog updates and certification metadata as agreed.
- **Request changes** — specific validator failures, missing README, or overstated claims.
- **Defer** — proposal is valuable but needs split PRs or pilot usage first.

## Escalation

Disagreements on risk-sensitive wording go to the maintainer group using [`../community/maintainer-guide.md`](../community/maintainer-guide.md) conventions (transparent decision notes in PR threads).
