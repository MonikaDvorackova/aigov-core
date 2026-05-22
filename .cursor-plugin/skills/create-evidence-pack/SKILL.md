---
name: create-evidence-pack
description: Create and offline-validate Governance Evidence Pack JSON; distinguish hosted CI artefact flows from local validators.
---

# Skill: Create and verify evidence packs (GovAI)

Use this skill when generating **CI evidence artefacts**, **governance evidence pack JSON**, or validating packs **offline** before submission.

## A. Governance Evidence Pack (standards document, offline)

For the **Governance Evidence Pack** standard (JSON/YAML file validated without network):

1. Author or update the document under your feature branch.
2. From repository root, run:

   ```bash
   python mcp/govai_mcp_server.py govai-verify-evidence-pack --path examples/standards/governance_evidence_pack.valid.json
   ```

   Replace the path with your document.

3. Interpret stdout: JSON with `"ok": true` and a stable `"digest"` means the document passes deterministic validators.

## B. CI artefact directory (hosted ledger path)

For **submit-evidence-pack / verify-evidence-pack** flows (requires a running audit service and credentials — **not** offline):

1. Follow **`docs/github-action.md`** and **`docs/manual-evidence-flow.md`** for `GOVAI_RUN_ID`, manifest layout, and digest continuity.
2. Use the composite action or `govai` CLI **outside** this offline MCP wrapper when network and secrets are available.

## C. Repository Makefile helpers

When a full run pipeline is needed locally (requires audit service):

- `make evidence_pack RUN_ID=<uuid>` — generates pack artefacts via Python tooling (see `Makefile`).

## D. Done criteria

- Offline validation: `govai-verify-evidence-pack` returns exit code `0` and `"ok": true`.
- Hosted path: `verify-evidence-pack` exits `0` with required export flags per your organisation policy.
