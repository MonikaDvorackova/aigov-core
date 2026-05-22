# GovAI Cursor plugin — Marketplace submission draft

## Product name

GovAI

## Tagline

Build auditable AI systems with deterministic governance gates.

## Short description

Deterministic AI governance for your repository: local compliance checks, evidence-pack validation, audit-report scaffolding, and Cursor rules that keep agents aligned with your merge gates.

## Long description

GovAI packages **Cursor rules**, **Agent skills**, and a **local MCP server** so development teams can run the same classes of checks that matter for compliance reviews—pytest, markdown audit gates, Makefile `gate`, and offline **Governance Evidence Pack** validation—without leaving the IDE.

The integration is **repository-local** by default: subprocess calls use explicit argument lists, timeouts, and structured JSON responses. A dedicated **dry-run** mode previews audit report templates without writing files. Read-only tools are separated from write-capable tools in documentation and responses.

Organisations keep **CI and hosted audit services** as the source of truth for production verdicts; the plugin is an accelerator and consistency layer for developers and AI agents.

## Categories

- Infrastructure / Agent Orchestration
- Developer productivity / Compliance tooling

## Target users

- Platform and compliance engineers maintaining AI governance pipelines.
- Developers on GovAI-integrated repositories who want IDE-native gate checks.
- Teams preparing EU AI Act–aligned documentation and evidence packs (non-legal workflow support).

## Key capabilities

- Cursor **rules** for branch policy, audit-report requirements, and compliance gates.
- **Skills** for triaging gate failures, creating evidence packs, preparing audit reports, and mapping controls.
- **MCP tools**: pytest runner, evidence validation, report heading gate, `make gate`, audit template generation with **dry-run**.
- **Validation scripts** for plugin integrity and smoke testing (`scripts/validate_cursor_plugin.py`, `scripts/smoke_cursor_plugin.py`).

## Demo workflow

1. Open the repository in Cursor and add the MCP server from **`plugin.json`** / **`.cursor-plugin/mcp.json`** or merge **`examples/local-config.json`** into **`.cursor/mcp.json`**.
2. Run **govai_verify_evidence_pack** on `examples/standards/governance_evidence_pack.valid.json`.
3. Run **govai_gate_reports** to confirm `docs/reports` headings.
4. Run **govai_generate_audit_report_template** with `dry_run: true` (or `--dry-run`) to preview a new report path and body.
5. Enable rules and ask Agent to follow **fix-compliance-gate** if a CI gate fails.

## Required screenshots

1. Cursor MCP panel showing `govai-local` connected and a successful **govai_gate_reports** result.
2. Agent using a bundled **skill** (for example prepare-audit-report) with visible command references.
3. Evidence pack validation success for the example JSON file.
4. Audit template **dry-run** output showing `wrote_file: false` and preview text.
5. Rules list or diff showing `.mdc` titles and descriptions in Cursor.

## Limitations

- **Not** a certified compliance product; organisational policies and hosted services remain authoritative.
- MCP server is a **minimal** stdio implementation, not a full-featured remote MCP deployment.
- **Linux/macOS-oriented** examples; Windows paths may need adjustment in local MCP config.
- Full `make gate` can be slower than `gate_reports` alone; timeouts may need tuning on very large monorepos.

## Support policy

- **Open-source / internal** support model: issues and contributions via the repository’s normal channels (as defined by project maintainers).
- No guaranteed SLA for Marketplace installs unless the vendor organisation contracts separately.

## Licensing considerations

- Plugin content (rules, skills, manifest) ships with the **repository license**; confirm compatibility before Marketplace listing.
- Third-party dependencies (Python venv, pytest, Rust toolchain) are **not** bundled; users must comply with those licenses separately.

## Submission checklist

- [ ] Confirm `plugin.json` fields match Marketplace character limits and formatting rules.
- [ ] Attach required screenshots and a short demo video (if requested by Cursor).
- [ ] Document minimum Cursor version and tested OS targets.
- [ ] Privacy statement: no telemetry added by default MCP paths; local execution only.
- [ ] Run `make cursor-plugin-check` and capture logs for maintainer review.
- [ ] Legal/marketing review that taglines do not imply regulatory certification.
