---
name: Bug report
about: Report a bug in GovAI Core (aigov_audit runtime, SDK, or core CI)
title: "[BUG] "
labels: bug
assignees: ""
---

## Summary

Describe the bug clearly (runtime ingest, compliance summary, export, verify, tenant isolation, or core tooling).

## Steps to reproduce

1.
2.
3.

## Expected behavior

Describe expected behavior.

## Actual behavior

Describe actual behavior.

## Environment

- OS:
- Python version:
- Rust version:
- GovAI Core context: local `aigov_audit` / integrator fork
- `AIGOV_ENVIRONMENT` (if relevant):
- Tenant mapping: `GOVAI_API_KEYS` + `GOVAI_API_KEYS_JSON` configured? (yes/no — do not paste secrets)

## Governance surface (if relevant)

- Does this involve **CI gates**, **`govai check`**, **`GET /compliance-summary`**, **`GET /verify`**, or **`docs/reports/`** headings?
- If yes, paste **redacted** JSON snippets or log lines (no API keys).

## Triage hints (optional)

Maintainers route issues using **[`docs/community/issue-triage.md`](../../docs/community/issue-triage.md)**. Mention if you believe this is **`good first issue`** / **`help wanted`** material.

## Logs / screenshots

Add relevant logs or screenshots if available.
