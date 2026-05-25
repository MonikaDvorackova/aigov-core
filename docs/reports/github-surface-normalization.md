# GitHub Surface Normalization

## Summary

Normalized the **GitHub operational surface** of GovAI Core so the repository presents as an open-source, ledger-authoritative audit runtime (`aigov_audit`). Updated issue and PR templates, discussion templates, `config.yml` contact links, `CODEOWNERS`, composite action description, and operator support doc. No runtime semantics changed.

## Evaluation gate

Evaluation evidence remains **ledger-authoritative** (`evaluation_reported` and related types). GitHub templates and discussions must not imply that CI or integrators may override deterministic **compliance summary** verdicts from side channels. Evaluation-related issues should reference `GET /compliance-summary` and redacted ledger/export JSON, not hosted billing or dashboard state.

## Human approval gate

Human approval evidence remains **ledger-authoritative** (`human_approved`, `risk_reviewed`, and related types). GitHub templates direct governance RFCs and security reports to preserve approval and promotion invariants. Discussion and issue flows must not treat `X-GovAI-Project` as a tenant security boundary.

## Repository presentation

| Asset | Before | After |
|-------|--------|-------|
| `ISSUE_TEMPLATE/config.yml` | Links to `aigov-compliance-engine` | Links to `MonikaDvorackova/govai-core` |
| Issue templates | Generic “GovAI”; onboarding/hosted framing | **GovAI Core** scope; platform called out as separate |
| `pull_request_template.md` | Staging workflow only | Staging workflow + core invariants + check matrix |
| `DISCUSSION_TEMPLATE/` | Missing | General, Integrations, Governance categories |
| `SUPPORT.md` | Missing | Core support routing |
| `CODEOWNERS` | “onboarding materials” | “reference integrations” + `api/` |
| `govai-check` action | “hosted evaluation” wording | Ledger-authoritative compliance summary |
| `FUNDING.yml` | Missing | Manual follow-up (optional) |

README, SECURITY, CONTRIBUTING, and GOVERNANCE were already aligned from prior OSS normalization; not duplicated in this PR.

## GitHub operational cleanup

### Git-tracked (this PR)

- `.github/ISSUE_TEMPLATE/*` — GovAI Core descriptions, tenant/API key hints, platform exclusion
- `.github/pull_request_template.md` — `staging` target, invariant checklist, verification commands
- `.github/DISCUSSION_TEMPLATE/*` — new discussion forms
- `.github/SUPPORT.md` — support matrix
- `.github/CODEOWNERS` — comments and `api/` ownership
- `.github/actions/govai-check/action.yml` — description wording
- `.github/workflows/govai-smoke.yml` — clarify optional platform vs core CI

### Valid historical references (unchanged)

- `govai-ci.yml` / `compliance.yml` comments that hosted SaaS belongs to GovAI Platform
- Workflow `paths:` filters including `dashboard/**` (monorepo layout; does not mount dashboard on `aigov_audit`)
- `docs/hosted/`, `docs/billing/` in README as **platform reference only**

### Manual metadata (Part B — not executed in this PR)

See recommended `gh` commands below. Maintainer must run after review.

## Verification

```bash
make gate
make reference-integrations-check
make core-runtime-examples-check
```

No Rust or runtime code changes in this PR.

---

## Appendix: recommended GitHub metadata commands (Part B)

**Do not run blindly.** Review org permissions and current repo settings first (`gh repo view MonikaDvorackova/govai-core`).

### 1. Repository description and topics

```bash
gh repo edit MonikaDvorackova/govai-core \
  --description "Open-source ledger-authoritative AI governance audit runtime (aigov_audit): append-only evidence, deterministic compliance summary, audit export, verify." \
  --add-topic govai \
  --add-topic ai-governance \
  --add-topic audit-runtime \
  --add-topic evidence-ledger \
  --add-topic rust \
  --add-topic python \
  --homepage "https://github.com/MonikaDvorackova/govai-core#readme"
```

Remove stale topics if present (adjust per `gh label list` / repo settings UI):

```bash
gh repo edit MonikaDvorackova/govai-core \
  --remove-topic compliance-engine \
  --remove-topic saas \
  --remove-topic billing
```

### 2. Discussions

```bash
gh repo edit MonikaDvorackova/govai-core --enable-discussions
```

Suggested **categories** (create in GitHub Settings → Discussions → Categories if not using templates only):

| Category | Purpose |
|----------|---------|
| General | Questions about GovAI Core runtime and docs |
| Integrations | App/CI integration patterns |
| Governance & standards | Portable standards, policy packs, RFC ideas |
| Announcements | Releases and maintainer notices (maintainers only post) |

### 3. Suggested pinned discussions (create then pin in UI)

1. **“GovAI Core quickstart — evidence → compliance summary → export → verify”** — link `docs/quickstart-runtime.md`
2. **“Reference integrations index”** — link `docs/reference-integrations.md`
3. **“Contributing: staging branch workflow”** — link `CONTRIBUTING.md` branching section

### 4. Branch protection (staging and main)

Inspect current rules:

```bash
gh api repos/MonikaDvorackova/govai-core/branches/staging/protection
gh api repos/MonikaDvorackova/govai-core/branches/main/protection
```

Recommended policy (apply via Settings or `gh api` when ready):

- **`staging`**: require PR, require `govai-ci` / `govai-core-portable` status, no force push
- **`main`**: require PR from `staging` only for maintainers, stricter checks + `release-validation` on promotion PRs

Example (illustrative — IDs vary per repo):

```bash
# Requires admin; customize contexts to match your required checks
gh api repos/MonikaDvorackova/govai-core/branches/staging/protection \
  --method PUT \
  -f required_status_checks='{"strict":true,"contexts":["govai-core-portable"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"required_approving_review_count":1}' \
  -f restrictions=null
```

### 5. Release and tag strategy

| Artifact | Strategy |
|----------|----------|
| **Git tags** | Semver `vMAJOR.MINOR.PATCH` on `main` after staging promotion; pre-releases `vX.Y.Z-rc.N` on `staging` optional |
| **GitHub Releases** | Release notes from `CHANGELOG.md`; attach `aigov_audit` build instructions, not platform SaaS bundles |
| **Composite Action** | Tag `v1` / `v1.x` on `govai-core` (not legacy `aigov-compliance-engine` name) |
| **PyPI** | Separate pipeline per `docs/releases/npm-typescript-publishing.md` / Python release docs |

```bash
# Example maintainer release (after checklist)
git switch main && git pull
make release-readiness-check
gh release create v1.0.0 --generate-notes --target main
```

### 6. Social preview

Upload repository social preview image (Settings → General → Social preview) showing **GovAI Core** + “ledger-authoritative audit runtime”. No Stripe/dashboard imagery.

### 7. Milestones (suggested)

| Milestone | Focus |
|-----------|--------|
| Core runtime hardening | Ledger, tenant isolation, export schema |
| Reference integrations | Examples + docs |
| Standards interchange | Portable validators, registry |
| Platform split hygiene | Docs clearly labeled platform-only |

```bash
gh api repos/MonikaDvorackova/govai-core/milestones -f title="Core runtime hardening" -f state=open
```

### 8. Labels — add (if missing)

```bash
gh label create "runtime" --color "1D76DB" --description "aigov_audit HTTP runtime" -R MonikaDvorackova/govai-core
gh label create "integrations" --color "0E8A16" --description "Reference integrations and SDK adoption" -R MonikaDvorackova/govai-core
gh label create "tenant-isolation" --color "B60205" --description "API key tenant mapping / isolation" -R MonikaDvorackova/govai-core
gh label create "audit-export" --color "5319E7" --description "aigov.audit_export.v1 and verify" -R MonikaDvorackova/govai-core
gh label create "platform-out-of-scope" --color "FBCA04" --description "GovAI Platform; redirect or close per scope" -R MonikaDvorackova/govai-core
```

### 9. Labels — delete or repurpose (review first)

List all labels:

```bash
gh label list -R MonikaDvorackova/govai-core --limit 100
```

Candidates to **delete** if unused and misleading (verify no open issues first):

```bash
# Examples only — replace NAME with actual stale labels from `gh label list`
gh label delete "saas" -R MonikaDvorackova/govai-core --yes
gh label delete "billing" -R MonikaDvorackova/govai-core --yes
gh label delete "onboarding" -R MonikaDvorackova/govai-core --yes
gh label delete "hosted-dashboard" -R MonikaDvorackova/govai-core --yes
gh label delete "kovali" -R MonikaDvorackova/govai-core --yes
```

### 10. Enable security features (recommended)

```bash
gh api repos/MonikaDvorackova/govai-core -X PATCH \
  -f has_issues=true \
  -f has_wiki=false \
  -f has_projects=true
```

Enable Dependabot / code scanning via GitHub Settings (or existing `security-scan.yml` workflow).
