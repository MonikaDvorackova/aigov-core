# Marketplace demo flow (reviewer script)

## Preconditions

- Cursor current stable channel.
- Repository opened at **workspace root** (contains **`python/`**, **`rust/`**, **`.cursor-plugin/`**).
- Python **3.10+** with **`python/.venv`** installed per contributor docs.

## Flow (12 minutes)

1. **Introduce the problem (1 min)** — show a failing CI log snippet (redacted) where markdown audit headings were missing.
2. **Wire MCP (2 min)** — add the local server from **`.cursor-plugin/mcp.json`** / **`plugin.json`** or merge **`.cursor-plugin/examples/local-config.json`** into **`.cursor/mcp.json`**; restart MCP; confirm connection.
3. **Read-only gate (2 min)** — run **`govai_gate_reports`**; show JSON with `"ok": true` on a clean tree.
4. **Evidence pack validation (3 min)** — run **`govai_verify_evidence_pack`** on **`examples/standards/governance_evidence_pack.valid.json`**; show success object.
5. **Dry-run audit template (2 min)** — run **`govai_generate_audit_report_template`** with **`dry_run: true`**; expand preview text; confirm no disk write.
6. **Agent skill (2 min)** — ask the agent to follow the **`fix-compliance-gate`** skill (`skills/fix-compliance-gate/SKILL.md`) for a synthetic heading omission in a scratch buffer (do not commit).

## Expected reviewer takeaways

- Clear separation between **read-only** diagnostics and **write** tools.
- Deterministic JSON responses suitable for automation.

## Closing line

“CI remains the contract; Cursor becomes the rehearsal studio.”
