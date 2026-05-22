# Contributor pathways

GovAI benefits from contributors who deepen **auditability**, **interoperability**, and **operator clarity**—while preserving **fail-closed** defaults and **single-verdict authority**.

## Pathway A — Documentation and education

**Outcome:** faster onboarding for OSS users, pilots, and customers.

- Start: [first contribution guide](first-contribution-guide.md)
- Grow: own a vertical doc (for example “Windows dev”, “Air-gapped export”) under `docs/`
- Collaborate: keep **govbase.dev** reader docs aligned with canonical Markdown under `docs/`

## Pathway B — Examples and integrations

**Outcome:** copy-pasteable pipelines that respect **`GOVAI_RUN_ID`** discipline.

- Start: extend `examples/ci/` or `examples/public-demo/` README flows
- Grow: language-specific snippets (GitLab CI, Buildkite) **without** weakening digest/export narrative
- Guardrail: document **`govai check`** vs **composite verify-evidence-pack** honestly ([github-action.md](../github-action.md))

## Pathway C — Standards and interchange

**Outcome:** portable JSON artefacts with stable digests.

- Start: read [standards README](../standards/README.md)
- Grow: new `examples/standards/*.valid.json` **with** evaluation harness updates when required
- Collaborate: schema docs under `docs/standards/`

## Pathway D — Core services (Rust / Python core)

**Outcome:** safer, faster audit service and CLI.

- Start: read [architecture overview](../architecture/overview.md), [CONTRIBUTING.md](../../CONTRIBUTING.md)
- Expect: integration tests, possible audit report, stricter review
- **Non-goals for drive-by PRs:** changing verdict semantics, loosening ingest validation, or altering migrations without operator runbook updates

## Pathway E — Cursor plugin and IDE ergonomics

**Outcome:** in-repo skills for evidence packs and gate debugging.

- Start: [.cursor-plugin/README.md](../../.cursor-plugin/README.md)
- Run: `make cursor-plugin-check`
- Grow: new skills that **link** to canonical governance docs (skills are not a second product contract)

## Recognition

Maintainers may highlight contributors in release notes or Discord; there is no automated points system—quality and reviewability matter more than volume.

## Related

- [Contributor workflow](../project/contributor_workflow.md)
- [Phase 6 public launch audit](../reports/repo-debt-audit-and-cleanup.md)
