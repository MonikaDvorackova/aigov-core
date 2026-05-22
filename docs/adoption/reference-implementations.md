# Reference implementations and adoption kits

This page indexes **runnable or copy-paste adoption kits** under `examples/adoption/`. Use them together with **`docs/adoption/quickstart-matrix.md`** to pick a path by role and time budget.

## Reference kits

| Kit | Path | What you get |
|-----|------|----------------|
| **GitHub Actions CI gate** | `examples/adoption/github-actions-ci-gate/` | Workflow template + `sample-evidence.json`; **no secrets** for default JSON validation; optional hosted gate behind `GOVAI_ADOPTION_ENABLE_HOSTED_GATE`. |
| **Self-hosted enterprise (Compose)** | `examples/adoption/self-hosted-enterprise/` | `docker-compose.example.yml` + `.env.example` to run Postgres + audit API from a clone. |
| **AI Act evidence workflow** | `examples/adoption/ai-act-evidence-workflow/` | Interchange JSON samples (`evidence-pack`, `policy-module`, `decision-trace`) for offline validation. |
| **Standards conformance** | `examples/adoption/standards-conformance-kit/` | `run-conformance.sh` + `sample-valid-artifact.json` wired to `scripts/validate_standard_conformance.py`. |

## Documentation companions

- **Role / time matrix** — `docs/adoption/quickstart-matrix.md`
- **Operator evaluation** — `docs/adoption/operator-evaluation-guide.md`
- **Narrative integration guides** — `docs/examples/*.md` and `examples/reference/*/README.md`

## Non-goals

These kits **do not** replace `docs/github-action.md`, `docs/hosted-backend-deployment.md`, or security review packs. They **do not** certify legal compliance and **do not** modify core **verdict** or **digest** semantics.

## Validation

From the repository root:

```bash
make adoption-kits-check
make reference-implementations-check
```

## Related

- `docs/launch/community-outreach.md` · `docs/launch/design-partners.md` · `docs/reports/repo-debt-audit-and-cleanup.md`
