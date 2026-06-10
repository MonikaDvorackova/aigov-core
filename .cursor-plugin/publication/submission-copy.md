# Cursor Marketplace — submission copy (AIGov)

**Publication status:** submission-ready in this repository; **not live** and **not approved** in Cursor Marketplace. See [`status.md`](status.md).

## Product name

AIGov

## Tagline

Deterministic governance gates and audit-ready evidence workflows inside Cursor.

## Short description (≤400 characters)

AIGov for Cursor bundles rules, Agent skills, and a local MCP bridge so developers run pytest, audit-report heading gates, Makefile `gate`, and offline governance evidence validation from the IDE. Read-only diagnostics are separated from write tools with dry-run previews. CI and hosted audit services remain authoritative.

## Long description

AIGov turns your compliance-engine repository into an **IDE-native governance assistant**. Cursor **rules** enforce branch policy, audit-report conventions, and merge-gate expectations. **Skills** guide agents through gate triage, evidence-pack validation, audit report authoring, and EU AI Act–oriented mapping (non-legal, operational only). A **minimal stdio MCP server** (`govai-local`) wraps existing repository scripts with explicit argument lists, timeouts, and structured JSON responses.

**Read-only tools** cover pytest, offline Governance Evidence Pack validation, markdown audit heading checks, and optional full `make gate`. **Write-capable** audit template generation supports **`dry_run`** so reviewers can preview report bodies without disk writes.

The plugin accelerates **local** iteration. It does **not** replace hosted AIGov verdicts (`GET /compliance-summary`), Rust runtime enforcement, database policy, or organisational controls. It is **not** a certified compliance product.

**Workspace requirement:** open the **full AIGov repository** as the Cursor workspace root so `mcp/govai_mcp_server.py` and `python/` resolve correctly.

## Categories (pick closest Marketplace labels)

- Developer productivity
- Security / compliance tooling

## Support expectations

- Community best-effort via GitHub issues (see [`support-and-contact.md`](support-and-contact.md)).
- No SLA for Marketplace installs unless a separate commercial agreement exists.
- Enterprise hosted support: `docs/commercial/support-and-sla.md`.

## Limitations

- Not regulatory certification; organisational policies remain authoritative.
- Local stdio MCP only — not a managed remote MCP SaaS.
- Full `make gate` may be slower than heading-only checks; tune MCP timeouts on large monorepos.
- Windows paths may need local MCP config adjustments (macOS/Linux primary).

## Licensing notes

- Plugin assets ship under the **repository license** (`plugin.json` `license` field).
- Python, pytest, and Rust toolchains are operator-provided; their licences apply independently.

## Privacy statement (listing)

- Default MCP tools run **locally** without added vendor telemetry from this pack.
- No production API keys required for read-only smoke validation.
