# Cursor Marketplace plugin package audit

## Summary

This change adds the AIGov Cursor Marketplace plugin package to govai-core.

The package includes Cursor plugin metadata, rules, skills, local MCP server entrypoints, marketplace listing assets, publication documentation, validation scripts, and publication tests.

## Evaluation gate

Validation performed:

- `python3 scripts/validate_cursor_plugin.py`
- `python3 scripts/validate_cursor_marketplace_listing.py`
- `pytest python/tests/test_cursor_marketplace_publication.py -v`

Observed result:

- Cursor plugin validation passed.
- Cursor Marketplace listing validation passed.
- Cursor Marketplace publication tests passed: 7 passed.

## Human approval gate

This report confirms that the package is suitable for review in the staging branch.

The plugin is not marked as live in Cursor Marketplace. Public publication remains subject to external Cursor approval and any required legal or marketing review.
