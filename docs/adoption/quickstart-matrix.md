# Quickstart matrix

Pick a **concrete** starting point by **role** and **time available**. All paths are **local or copy-paste** unless you explicitly enable hosted CI variables.

## Quickstart matrix

| Role | Time | Kit / doc | Outcome |
|------|------|-----------|---------|
| **Platform / CI engineer** | ~15 min | `examples/adoption/github-actions-ci-gate/` | Validated workflow + sample JSON; optional hosted gate when configured. |
| **Operator / SRE** | ~30 min | `examples/adoption/self-hosted-enterprise/` | Local Postgres + audit API via Compose (dev keys only). |
| **Governance / policy** | ~20 min | `examples/adoption/ai-act-evidence-workflow/` | Offline interchange JSON validated with `validate_standard_conformance.py`. |
| **Standards author** | ~10 min | `examples/adoption/standards-conformance-kit/` | One-command offline conformance for a sample evidence pack. |
| **Executive / PM** | ~10 min | `docs/adoption/operator-evaluation-guide.md` | Evaluation criteria without running services. |

## Hosted pilot (optional, operator-mediated)

When you move beyond kits, use **`docs/hosted-pilot-runbook.md`** and **`docs/customer-onboarding-10min.md`** — these require **API keys** and a **live** `GOVAI_AUDIT_BASE_URL`.

## Related

- `docs/adoption/reference-implementations.md`
