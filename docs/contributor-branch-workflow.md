# Contributor branch workflow

GovAI uses a staged contribution workflow.

Normal contributor flow:

```text
feature branch -> staging
```

Maintainer release flow:

```text
staging -> main
```

## For contributors

Create a dedicated branch for every contribution:

```bash
git checkout -b docs/human-approval-gate
```

Open the pull request into `staging`, not `main`.

Correct:

```text
docs/human-approval-gate -> staging
```

Incorrect:

```text
main -> staging
main -> main
feature branch -> main
```

## Why this matters

GovAI is a governance and auditability project. Changes are reviewed and integrated through `staging` before they are promoted to `main`.

This keeps release history, compliance checks, and audit evidence consistent.
