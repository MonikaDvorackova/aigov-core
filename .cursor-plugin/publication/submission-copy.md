# Cursor Marketplace — submission copy (GovAI)

## Product name

GovAI

## Tagline

Deterministic governance gates and audit-ready evidence workflows inside Cursor.

## Short description (≤400 characters target)

Run the same classes of checks your merge gates care about—pytest, markdown audit headings, Makefile `gate`, and offline governance evidence validation—without leaving the editor. Repository-local MCP bridge with explicit read vs write tools.

## Long description

GovAI for Cursor bundles **rules**, **skills**, and a **minimal MCP server** so teams can keep AI agents aligned with branch policy, audit-report conventions, and evidence-pack validation. Read-only tools cover diagnostics; write-capable tools are documented separately and support **dry-run** previews for audit templates.

The integration complements **CI and hosted audit services**: it accelerates developer iteration but does not replace production verdicts from **`GET /compliance-summary`**.

## Categories (pick closest Marketplace labels)

- Developer productivity
- Security / compliance tooling

## Support expectations

- **Community best-effort** via the public repository issue tracker.
- **No SLA** for Marketplace installs unless a separate commercial agreement exists.

## Limitations

- Not a certified compliance product; organisational policies remain authoritative.
- MCP server is a **local stdio** helper, not a managed remote MCP SaaS.
- Full `make gate` can be slower than heading-only checks on very large trees; tune timeouts in MCP config if needed.

## Licensing notes

- Plugin assets ship under the **repository license**; confirm compatibility before listing.
- Python, pytest, and Rust toolchains are **operator-provided**; their licences apply independently.
