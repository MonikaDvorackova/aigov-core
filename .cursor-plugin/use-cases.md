# AIGov Cursor plugin — use cases

How different roles use the AIGov Cursor plugin together with the open source engine and optional hosted services. Capabilities depend on your deployment; this document describes **typical** patterns.

## AI startup CTO

**Goals:** Ship fast without losing auditability; align engineering with a single governance story before Series A diligence.

**Plugin usage:**

- Enforce **branch policy** and **audit-report** expectations via rules so agents do not claim “merge ready” without gates.
- Use **`govai-check`** and **`govai-gate-reports`** from MCP in daily development.
- Standardise **`docs/reports/*.md`** for security reviews and customer questionnaires using the audit-report skill.

**Outcomes:** Repeatable local checks, fewer last-minute documentation scrambles, clearer separation between OSS local workflow and future hosted audit.

## ML platform engineer

**Goals:** Wire CI, local dev, and evidence artefacts so model and pipeline changes leave a traceable compliance trail.

**Plugin usage:**

- Skills for **evidence-pack** validation and **compliance gate** triage when CI fails.
- MCP **`govai-verify-evidence-pack`** integrated into pre-commit or local smoke scripts (read-only).
- Rules to keep **evaluation** and **human approval** language consistent with hosted run semantics (documentation alignment; not a substitute for service configuration).

**Outcomes:** Faster root-cause on gate failures, consistent artefact shapes between local validation and hosted submissions.

## Compliance officer

**Goals:** Verify that engineering processes match internal policy; review audit reports and evidence without reading every line of code.

**Plugin usage:**

- Read **rules** as codified engineering policy (branch flow, gate requirements).
- Use **`docs/reports/`** outputs authored with `prepare-audit-report` skill headings for sign-off sections.
- Cross-check **EU AI Act mapping** skill output as operational guidance (not legal advice).

**Outcomes:** Clearer evidence of what was checked, by whom, and under which headings; fewer ad-hoc spreadsheets.

## Regulated enterprise

**Goals:** Strong access controls, retained audit history, private deployments, and contractual SLAs — often beyond pure OSS.

**Plugin usage:**

- OSS plugin for **developer IDE consistency** on top of a **private** or **hosted** AIGov backend (per contract).
- Enterprise features (SSO, RBAC, retention) apply to the **service** and organisation controls; see [../docs/commercial/enterprise-features.md](../docs/commercial/enterprise-features.md).

**Outcomes:** Developers get the same Cursor-native experience while central IT maintains authoritative enforcement and identity.

## Open source contributor

**Goals:** Land high-quality PRs that pass community CI and respect governance conventions.

**Plugin usage:**

- `make cursor-plugin-check` before pushing.
- Follow **`compliance-gate.mdc`** so pytest, Rust tests, and report gates are green locally.
- Add **exactly one** focused `docs/reports/*.md` entry when the change warrants an audit trail per project rules.

**Outcomes:** Fewer CI round-trips, clearer expectations for report content, better reviewer experience.
