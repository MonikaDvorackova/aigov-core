# Good first issues (curated themes)

This page complements GitHub’s **`good first issue`** label: it explains **what kinds of first contributions** fit GovAI’s governance model and which areas need **senior review**.

## Safe starter themes (usually fast review)

| Theme | Examples | Skills |
| --- | --- | --- |
| **Documentation** | Clarify README sections, fix broken relative links, extend troubleshooting | Markdown |
| **Examples** | Add JSON samples under `examples/`, improve READMEs for demos | JSON, narrative |
| **Public docs** | Clarify `docs/*.md` used by **govbase.dev** `/docs` and `/help`; fix relative links | Markdown |
| **Developer experience** | Makefile targets that wrap existing scripts (no policy change) | Make, shell |

## Good but moderate complexity

| Theme | Examples | Notes |
| --- | --- | --- |
| **CI ergonomics** | Better error messages in workflows **without** removing jobs | Coordinate in issue first |
| **Python CLI** | UX flags, help text, tests | Run `pytest` |
| **Standards tooling** | Validators for interchange JSON under `python/aigov_py/standards/` | Run evaluation harness when touching golden files |

## High-sensitivity (not “good first” without design)

| Area | Why |
| --- | --- |
| **Rust audit / enforcement** | Affects append-only behaviour and verdict projection |
| **Database migrations** | Operator and data lifecycle impact |
| **Verdict semantics** | Customer contracts and CI meaning |
| **CI governance gate removal** | Forbidden for contributor PRs without explicit maintainer governance decision |

If you are excited about these areas, open a **design discussion issue** first and link prior art from `docs/governance/`.

## How issues are picked

1. Filter labelled **`good first issue`**.
2. Prefer issues with **acceptance criteria** and **non-goals** spelled out.
3. Ask for assignment if the issue is stale >14 days.

## Related

- [First contribution guide](first-contribution-guide.md)
- [Contributor pathways](contributor-pathways.md)
- [Label taxonomy](../project/label_taxonomy.md)
