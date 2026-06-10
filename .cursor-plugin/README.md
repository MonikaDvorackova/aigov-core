# AIGov — Cursor plugin (rules, skills, local MCP)

## Overview

This package turns the AIGov compliance engine repository into an **IDE-native governance assistant** for Cursor: deterministic **rules** (branch flow, audit expectations, compliance gates), **Agent skills** (gate triage, evidence-pack validation, audit authoring, EU AI Act–oriented mapping guidance), and a **local MCP bridge** (`mcp/govai_mcp_server.py`) that wraps existing repo scripts and tests.

The hosted audit service, Rust runtime enforcement, database migrations, and CI workflows remain **authoritative** for production compliance. The plugin accelerates **local** checks and consistent agent behaviour; it does not replace organisational controls.

**Publication status:** internally usable from a full repo clone; **submission-ready** documentation and asset manifest; **not live** and **not approved** in Cursor Marketplace — see [`publication/status.md`](publication/status.md).

**Marketplace publication package:** listing copy, demo flow, reviewer notes, support contacts, version policy, and release checklist live under **`publication/`** (start at [`publication/README.md`](publication/README.md)).

**Manifest schema:** `plugin.json` follows the **Cursor Marketplace–oriented** layout (`name`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `logo`, `rules`, `skills`, `mcpServers`). The Marketplace **slug** is the manifest `name` (`govai`); **AIGov** remains the product name in prose and listing copy.

**Internal / historical manifest fields** (for example `schema_version`, `tagline`, `bundles`, `mcp.entry`) are no longer carried in `plugin.json`; submission taglines and categories live in [`marketplace.md`](marketplace.md) and [`publication/submission-copy.md`](publication/submission-copy.md).

## Local installation

1. **Branching** — Work on a **feature branch**. Do not push directly to `main` or `staging` (see `rules/branch-policy.mdc`).
2. **Rules** — Copy or symlink `rules/*.mdc` into your project `.cursor/rules/` (or equivalent supported by your Cursor version), or consume via Marketplace when published.
3. **Skills** — Copy each `skills/<skill-name>/` directory (each contains `SKILL.md` with YAML frontmatter) into a Cursor skills tree your team uses (for example `.cursor/skills/govai/`) so Agent can discover them.
4. **MCP** — Use **plugin-level** [`.cursor-plugin/mcp.json`](mcp.json) and/or the `mcpServers` block in `plugin.json` as the canonical definition of `govai-local`. For workspace-local Cursor config, merge **`examples/local-config.json`** into **`.cursor/mcp.json`** (or use **`.cursor/mcp.json.example`** at the repo root). Adjust `command` if `python3` is not on your `PATH`.
5. **Python environment** — Evidence validation and pytest tools expect the **`python/.venv`** project virtualenv when present (see `Makefile` / `python/` layout). Restart Cursor after MCP changes.

## MCP stdio configuration

The **`govai-local`** server uses **stdio** and the same argv shape everywhere:

```json
{
  "mcpServers": {
    "govai-local": {
      "command": "python3",
      "args": ["mcp/govai_mcp_server.py", "mcp-stdio"],
      "env": {}
    }
  }
}
```

**Path resolution:** `args` paths are **relative to the repository root** (the workspace that contains `mcp/`). The server discovers the repo root via `.cursor-plugin/plugin.json` when possible.

**Marketplace vs clone-and-use:** When the plugin is consumed from a **full AIGov repository checkout** opened as the Cursor workspace root, repo-relative `args` work as above. If a Marketplace install exposes only the plugin subtree **without** the rest of the monorepo, `mcp/govai_mcp_server.py` will not exist next to the workspace — use a **full clone** for MCP-backed tools or copy the `govai-local` block into a workspace that points at your checkout (see **Remaining marketplace risks** below).

## Available tools

Exposed by `mcp/govai_mcp_server.py` (CLI subcommands mirror MCP tool names with kebab-case).

| Tool / CLI | Access | Purpose |
|------------|--------|---------|
| `govai_check` / `govai-check` | read-only | Runs `python -m pytest` from `python/` (uses venv interpreter when available). |
| `govai_verify_evidence_pack` / `govai-verify-evidence-pack` | read-only | Offline validation of a Governance Evidence Pack via `aigov_py.standards.cli`. |
| `govai_gate_reports` / `govai-gate-reports` | read-only | Runs `scripts/gate_reports.py` (required headings in `docs/reports/*.md`). |
| `govai_make_gate` / `govai-make-gate` | read-only | Runs `make gate` (full Makefile gate; heavier than `gate_reports` alone). |
| `govai_generate_audit_report_template` / `govai-generate-audit-report-template` | **write** | Creates `docs/reports/<stem>.md` with required headings. Use `--dry-run` or MCP `dry_run: true` for a **preview only** (no disk write). |

All subprocess invocations use **explicit argument lists** (no shell interpolation), **timeouts**, and structured JSON including `command`, `exit_code`, `stdout`, `stderr`, and `duration_ms` for executed commands. Large streams are truncated with `stdout_truncated` / `stderr_truncated` flags when needed.

## Available rules

| File | Purpose |
|------|---------|
| `rules/branch-policy.mdc` | Feature → staging → main; forbid direct pushes to protected branches. |
| `rules/audit-report-required.mdc` | Require `docs/reports/*.md` with evaluation, approval, risk, and rollback sections for enforcement-impacting work. |
| `rules/compliance-gate.mdc` | Require pytest, Rust tests, `gate_reports.py`, and `make gate` before merge-ready claims. |

## Available skills

Each skill lives under `skills/<kebab-name>/SKILL.md` with YAML frontmatter (`name`, `description`).

| Path | Purpose |
|------|---------|
| `skills/fix-compliance-gate/SKILL.md` | Diagnose and fix failing gates. |
| `skills/create-evidence-pack/SKILL.md` | Offline standards validation vs hosted artefact flows. |
| `skills/prepare-audit-report/SKILL.md` | Author `docs/reports/*.md` with required headings. |
| `skills/map-ai-act-controls/SKILL.md` | Map product features to governance artefacts (non-legal). |

## Security model

- **Local execution** — The MCP server runs as the developer user with workspace credentials; treat MCP as **privileged** in regulated environments.
- **No outbound network** in default tool paths (local pytest, local scripts, offline evidence validation). `govai_make_gate` runs `make gate`, which matches your Makefile definition (still local to the repo).
- **Path constraint** — Evidence pack validation rejects paths outside the repository root.
- **Write boundary** — Only `govai_generate_audit_report_template` mutates disk by default; **`dry_run`** previews without writing.
- **Timeouts** — Subprocess calls use bounded wall-clock limits to reduce hung-agent risk.

## Non-goals

- Not a substitute for **hosted** AIGov audit artefacts, **Rust** enforcement, or **database** policy.
- Not legal advice; EU AI Act mapping skill is **operational** guidance only.
- Not a full MCP SDK implementation — stdio JSON-RPC is intentionally minimal; extend if Cursor requirements evolve.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| MCP server fails to start | `python3 mcp/govai_mcp_server.py govai-gate-reports` from repo root; confirm `python3` and paths. |
| `govai_verify_evidence_pack` fails | Activate or create `python/.venv`; confirm `--path` is repo-relative or inside the repo. |
| `govai_check` errors on imports | Run `make` / project bootstrap so `python/.venv` exists and deps are installed. |
| `gate_reports` / `make gate` fails | Ensure every `docs/reports/*.md` includes `## Evaluation gate` and `## Human approval gate` (see `scripts/gate_reports.py`). |
| Template tool refuses to write | File exists; use `--force` or pick a new `--stem`. Use `--dry-run` first. |

**Automation** — `python3 scripts/validate_cursor_plugin.py` validates manifest, logo, rules, skills layout, MCP metadata, and bundle hygiene. `python3 scripts/smoke_cursor_plugin.py` runs read-only smoke checks against the MCP CLI.

## Readiness checklist

### Internally usable (clone-and-use — ready)

- [x] `plugin.json` with Marketplace-oriented metadata (`govai`, version, author, links, license, keywords, `logo`, `rules`, `skills`, `mcpServers`).
- [x] Plugin-level **`mcp.json`** plus workspace examples (`.cursor/mcp.json.example`, `examples/local-config.json`).
- [x] Non-empty rules, skill directories with `SKILL.md`, README, and `examples/local-config.json`.
- [x] `assets/logo.png` derived from `dashboard/brand/aigov-mark.ico` (lossless composite, no mark scaling).
- [x] Local MCP server with read/write separation and dry-run for audit templates.
- [x] Validation and smoke scripts plus `Makefile` targets `cursor-plugin-validate`, `cursor-plugin-smoke`, `cursor-plugin-check`.
- [x] CI runs **`make cursor-plugin-check`** on PRs and pushes to **`main`** / **`staging`** (see `.github/workflows/oss-developer-experience.yml`).

### Documentation-ready (repository — ready)

- [x] [`publication/status.md`](publication/status.md) states **not live** and **listing media incomplete**.
- [x] Full-repository MCP model documented ([`installation-model.md`](publication/installation-model.md), `installation-check` CLI).
- [x] Demo-flow CLI evidence committed; logo, hero, and screenshots committed in `marketplace-assets.json`.
- [x] Go/no-go checklists with evidence validation ([`pre-submit-checklist.md`](publication/pre-submit-checklist.md)).
- [x] Hero banner and five Cursor UI screenshots committed; `make cursor-marketplace-listing-check` passes.
- [ ] Legal/marketing sign-off and Cursor portal submit — **external**.

### Not live in Cursor Marketplace

The plugin is **not published**, **not approved**, and **not listed** in Cursor Marketplace. Do not imply a live listing in docs or screenshots until [`publication/status.md`](publication/status.md) is updated after actual approval.

### Remaining marketplace risks

- **Workspace root:** MCP `args` assume the **repository root** is the Cursor workspace. Nested workspaces or multi-root layouts may need adjusted paths or a wrapper script (not committed; document locally).
- **Partial installs:** A listing that ships **only** `.cursor-plugin/` without `mcp/` and `python/` cannot run `govai-local` as-is; governance semantics in rules/skills are unchanged, but **stdio MCP tools require the full checkout** (or a maintainer-published alternative server).

## Commercial distribution and onboarding

- [quickstart.md](quickstart.md) — installation, MCP wiring, first compliance check, evidence verification, audit reports, troubleshooting.
- [use-cases.md](use-cases.md) — CTO, ML platform, compliance, enterprise, and OSS contributor workflows.
- [assets/README.md](assets/README.md) — logo master, banners, screenshots, demo video guidance, branding, file naming.

Commercial collateral for sales and customer success lives under `docs/commercial/` (pricing, OSS vs hosted matrix, enterprise features, support and SLA, onboarding playbook, sales one-pager, marketplace submission checklist).

See also `marketplace.md` (submission index) and `docs/reports/cursor-marketplace-readiness.md` (readiness audit).
