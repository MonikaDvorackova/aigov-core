# Submission guidelines (policy packs and registry entries)

This page is the contributor-facing checklist for proposing new **policy packs** or **registry metadata** updates.

## Before you open a pull request

1. **Read the format** — [`../marketplace/policy-pack-format.md`](../marketplace/policy-pack-format.md) and an existing pack such as [`../../examples/marketplace/eu-ai-act-basic/`](../../examples/marketplace/eu-ai-act-basic/).
2. **Validate locally** — `python3 scripts/validate_policy_pack.py examples/marketplace/<your-pack>` must exit `0`.
3. **Update catalogs** — if the pack is curated, add it to [`marketplace/manifest.json`](../../marketplace/manifest.json) **and** [`registry/policy-pack-catalog.json`](../../registry/policy-pack-catalog.json) with consistent `id` and `path`.
4. **Pick capabilities honestly** — only use `capability_ids` defined in [`registry/capability-taxonomy.json`](../../registry/capability-taxonomy.json).
5. **Pick a certification level** — default new public examples to `community` unless maintainers have completed a verified review **in the same change** (rare).

## Repository expectations

- **Deterministic JSON** — stable key ordering, no trailing noise, UTF-8 without BOM.
- **Synthetic contact data** — example maintainers should use obviously invalid addresses (for example `govai-marketplace@example.invalid`).
- **No secrets** — never commit signing keys, tokens, or customer evidence.

## Legal and safety language

Avoid “certified compliant with …” unless you are quoting a third-party seal you actually hold. Prefer “aligned with documentation themes inspired by …”.

## Review SLA

Maintainers triage submissions under the routine described in [review-process.md](review-process.md). Large or high-risk proposals may be split across multiple pull requests after maintainer agreement.
