# Open Plugins validator completion

## Summary

Complete the Open Plugins repository layout migration.

## Changes

- Update scripts/validate_cursor_plugin.py to validate repository-root rules/, skills/, and mcp.json.
- Update scripts/cursor_marketplace_publication.py path resolution for repository-root Open Plugins assets.
- Update checklist evidence to reference repository-root rules/compliance-gate.mdc.

## Evaluation gate

- python3 scripts/validate_cursor_plugin.py — PASS
- make cursor-plugin-check — PASS

The validator now correctly validates the Open Plugins repository layout.

## Human approval gate

This change only updates plugin validation and publication tooling.

No runtime behavior or governance logic changes.
