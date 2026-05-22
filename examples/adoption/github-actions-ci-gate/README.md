# Adoption kit: GitHub Actions CI gate

**Purpose:** Give downstream teams a **copy-paste starting point** for GovAI in GitHub Actions: a workflow that **always** validates local sample JSON **without secrets**, plus an **optional** hosted composite-action gate controlled by a repository variable.

## Prerequisites

- A GitHub repository where you can add workflows.
- Python 3 available on `ubuntu-latest` runners (default) for JSON validation.
- For the **optional** hosted gate: hosted or self-hosted GovAI audit API, `GOVAI_RUN_ID`, and API key per `docs/github-action.md`.

## Quickstart

1. Copy the **contents** of this folder to the **root** of your application repository so you have:
   - `sample-evidence.json`
   - `.github/workflows/govai-check.yml`
2. Commit and push. Open a PR that touches `sample-evidence.json` or run **Actions → govai-adoption-kit-ci → Run workflow**.
3. Confirm the job **validate-sample-evidence-json** succeeds.

## Expected output

- **Default:** workflow completes green; log shows `python3 -m json.tool` succeeded on `sample-evidence.json`.
- **Optional gate:** only when `GOVAI_ADOPTION_ENABLE_HOSTED_GATE=true` — the composite action runs and enforces your configured artefact layout (you must supply a prior job or artifact upload; this kit does not build evidence packs for you).

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Workflow not listed | Workflows must live under **repository root** `.github/workflows/`, not nested monorepo paths. |
| `No such file sample-evidence.json` | Ensure you copied this kit to the repo **root** (same directory as `.github/`). |
| Hosted gate fails immediately | Verify `GOVAI_RUN_ID`, `GOVAI_AUDIT_BASE_URL`, `GOVAI_API_KEY`, and that `artefacts/` matches `docs/github-action.md`. |
| `download-artifact` missing | Expected until you add a producing job; use `continue-on-error` or remove the download step until artefacts exist. |

## Scope limitations

- `sample-evidence.json` is an **illustrative** payload shape for learning; your live policy may require different event types and field sets (`docs/manual-evidence-flow.md`).
- This kit does **not** modify GovAI **verdict semantics**, **digest** behaviour, or **tenant isolation** — it only shows CI wiring patterns.
- **No secrets are required** for the default JSON validation job.

## Related

- `docs/github-action.md` · `docs/examples/github-actions-integration.md` · `examples/reference/github-actions/README.md` · `docs/adoption/reference-implementations.md`
