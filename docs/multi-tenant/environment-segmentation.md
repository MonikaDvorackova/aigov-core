# Environment segmentation

[`environment-segmentation.json`](../../multi-tenant/environment-segmentation.json) describes how **development**, **staging**, and **production** differ in risk tier, allowed data classes, and promotion rules.

## Credentials and secrets

Separate credentials per environment are **required** in the model. Secret naming uses a conventional prefix pattern so operators can detect accidental cross-environment reuse during audits.

## Promotion

Production promotion requires recorded policy sign-off, an evidence bundle for the release candidate, and confirmation that no break-glass session is open. These are **process gates** for humans; they do not alter automated compliance verdict formulas.

## Data replication

Cross-region copies must pass classification review, and customer-managed keys per region are recommended for regulated workloads.
