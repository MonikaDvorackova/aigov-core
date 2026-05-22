# Reference: GitHub Actions + GovAI

This folder is a **reference hub** for CI integration. The canonical specification lives in the main repository docs; copy patterns from there into your own workflows.

## When to use this

- You run **GitHub Actions** and want merges blocked unless the **hosted** verdict is **VALID**.
- You want **digest-bound** evidence (recommended for production) or a lighter **`govai check`** smoke path.

## Quick links

| Goal | Location |
|------|----------|
| Full action inputs, exit codes, semantics | `docs/github-action.md` |
| Step-by-step integration guide | `docs/examples/github-actions-integration.md` |
| Example workflow fragment | `examples/ci/govai-check.yml` |
| Production gate in this repo | `.github/workflows/compliance.yml` |

## Checklist

1. Create **`GOVAI_RUN_ID`** (UUID) — stable for the release train you are gating.
2. Configure **`GOVAI_AUDIT_BASE_URL`** and secret **`GOVAI_API_KEY`**.
3. Produce **`evidence_digest_manifest.json`** and run JSON under **`artifacts_path`** expected by the composite action.
4. Pin the action to a **tag** or SHA you trust (`@v1` or newer as released).
5. Require the GovAI job in **branch protection**.

## Pitfall

**`github.run_id`** is not a substitute for **`GOVAI_RUN_ID`** unless you deliberately design it that way. The evidence run must be **one consistent identifier** end-to-end.

## Not in this folder

This reference does **not** ship a standalone runnable workflow by itself — it points to the **canonical** files above to avoid drift.
