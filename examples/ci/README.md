# CI example: artefact-bound GovAI gate

[`govai-check.yml`](govai-check.yml) is a **copy-paste workflow** for **downstream** repositories. It is **not** under `.github/workflows/` in this repo, so GitHub does **not** execute it here.

## What it demonstrates

- Download CI artefacts containing **`evidence_digest_manifest.json`** and **`<run_id>.json`**.
- Invoke the published composite action **`MonikaDvorackova/aigov-compliance-engine@v1`** with repository variables and secrets.

## Before you use it

- Read **[docs/github-action.md](../../docs/github-action.md)** for semantics (`submit-evidence-pack` + `verify-evidence-pack`, digest continuity, **`VALID`** requirement).
- Configure **`GOVAI_RUN_ID`**, **`GOVAI_AUDIT_BASE_URL`**, and secret **`GOVAI_API_KEY`** in your repo.
- Never commit real API keys; use GitHub **Secrets** and **Variables** only.
