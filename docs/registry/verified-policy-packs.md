# Verified policy packs

**Verified** packs (see [`registry/certification-levels.json`](../../registry/certification-levels.json)) satisfy additional maintainer review beyond **community** examples. This page sets expectations for authors and reviewers.

## Minimum bar for `verified`

- Compatibility section names the **exact** `govai.standards.governance_policy_module.v1` interchange (or documented successor) and any constraints.
- Evidence codes are **unique within the pack** and explained in the pack README.
- `python3 scripts/validate_policy_pack.py` and `python3 scripts/registry_check.py` pass on a clean checkout.
- No contradictory claims relative to [`../trust-model.md`](../trust-model.md).

## Packaging

Verified packs should ship:

- `manifest.json` and `policy-module.json` (or referenced interchange paths documented in README).
- `README.md` with scope, non-goals, and worked example commands.
- Optional `CHANGELOG.md` if the pack evolves quickly.

## Promotion from `community`

Promotion requires an explicit maintainer decision recorded in the pull request and an update to [`registry/policy-pack-catalog.json`](../../registry/policy-pack-catalog.json) `certification_level_id`.

## Enterprise additions

**Enterprise** may additionally require signed release tags and documented support contacts inside the operator’s private registry; those artefacts are intentionally **not** mandated in the public repo.
