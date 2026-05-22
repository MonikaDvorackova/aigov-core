# Cursor plugin — release checklist

## Before tagging or submitting

- [ ] `make cursor-plugin-check` passes on a clean tree.
- [ ] `plugin.json` fields (`name`, `tagline`, `description`, `category`, `bundles`, `mcp`) match Marketplace character limits after editing.
- [ ] Rules and skills contain **no** accidental scaffold tokens such as `TODO` / `FIXME` (the repository validator enforces this).
- [ ] `README.md` and `quickstart.md` reference the same command names as MCP tool descriptors.
- [ ] Screenshot set from **`screenshot-plan.md`** captured and stored per your org’s media policy.
- [ ] Legal/marketing review confirms copy does **not** imply regulatory certification.

## After publication

- [ ] Pin a discussion or release note with known limitations from **`submission-copy.md`**.
- [ ] Monitor issues for MCP path problems on Windows (best-effort; docs call out macOS/Linux first).

## Rollback

- Unpublish or downgrade listing per Cursor Marketplace guidance; repository tags remain historical.
