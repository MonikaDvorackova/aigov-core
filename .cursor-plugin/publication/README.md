# Cursor Marketplace — publication package

This folder is the **single place** for marketplace-facing copy, demo choreography, screenshot planning, and release checklists for the GovAI Cursor plugin.

| File | Purpose |
| --- | --- |
| [submission-copy.md](submission-copy.md) | Final listing text (short + long descriptions, categories, limitations) |
| [demo-flow.md](demo-flow.md) | Step-by-step demo suitable for reviewers |
| [screenshot-plan.md](screenshot-plan.md) | Ordered list of still images to capture |
| [release-checklist.md](release-checklist.md) | Maintainer steps before publishing a version |

## Support and licensing

- Support expectations and licence framing are summarised in **`release-checklist.md`** and **`submission-copy.md`**.
- The plugin remains **repository-local** by default; hosted GovAI verdicts stay authoritative for production.

## Validation

From the repository root:

```bash
make cursor-plugin-check
```

The same target runs in **`.github/workflows/oss-developer-experience.yml`** before **`make enterprise-readiness-check`**, so broken manifests or MCP smoke failures block merges to **`main`** and **`staging`**.

Internal vs listing scope: the plugin pack under **`.cursor-plugin/`** is **production-ready for internal clone-and-use** when this check passes; **this `publication/` folder** is the staging area for **marketplace listing** copy, screenshots, and maintainer release steps that are still **maintainer-owned** and not implied complete until those artefacts exist.
