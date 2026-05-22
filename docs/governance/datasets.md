# Dataset governance (identity, digest, approval, lineage primitives)

Phase 3 M4 introduces **standalone dataset governance metadata** and deterministic validation helpers for dataset identity, cryptographic digests, human approval separation of duties, and lineage references. This slice does **not** connect to runtime policy enforcement or storage.

## Scope

- **In scope**: `DatasetStatus`, `DatasetClassification`, `DatasetRecord`, `DatasetApproval`, `DatasetLineageRef`, and pure-Python validators (`validate_dataset_record`, `validate_dataset_approval`, `validate_dataset_lineage`).
- **Out of scope**: runtime enforcement wiring, HTTP APIs, database migrations, ledger writes, compliance-summary behavior, dataset storage, raw dataset ingestion, or embedding raw dataset contents in audit or governance metadata.

## Purpose

These primitives establish **dataset identity** and **integrity digests** (content-addressing hints), **approval metadata** with separation between owner and approver, and **lineage references** that bind a dataset id to a digest. Later phases can wire them into evaluation, HIGH-risk policies, and AI Act evidence mapping—especially where **dataset lineage** must be demonstrated for high-risk systems.

## Statuses

| Status            | Meaning (primitive)                                    |
|-------------------|--------------------------------------------------------|
| REGISTERED        | Dataset registered in governance metadata model.       |
| APPROVAL_PENDING  | Awaiting approval (governance only).                 |
| APPROVED          | Approved under current governance rules.               |
| REJECTED          | Rejected; not approved for downstream use in wiring. |
| REVOKED           | Prior approval revoked.                              |

## Classification

Allowed values: **PUBLIC**, **INTERNAL**, **CONFIDENTIAL**, **RESTRICTED**. Callers must not place raw dataset payloads in these fields—only governance labels.

## Digest format

`dataset_digest` must be **64 hexadecimal characters** or **`sha256:`** followed by **64** hex characters (case-insensitive hex digits).

## Approvals

Approvals require a non-empty **approver_id**. The **owner** of the dataset (identified by `DatasetRecord.owner` when validating against a record) **cannot** be the same principal as the approver (separation of duties). If **expiration** is set on `DatasetApproval`, it must be **timezone-aware UTC**.

## Lineage

`DatasetLineageRef` carries `dataset_id` and `dataset_digest`. When validated against a `DatasetRecord`, the lineage id and digest must match the record (digests compared in canonical form, so bare hex and `sha256:` forms are equivalent when they denote the same hash).

## Fail-safe behavior and determinism

Validators return **sorted tuples of stable error strings**. The same inputs yield the same errors. Unknown dataset **status** strings fail validation. Invalid digests and classifications fail explicitly.

## Future runtime wiring

When enforcement is added, **HIGH**-risk or sensitive policies should require **valid lineage** tied to approved datasets before allowing uses that depend on training or evaluation data provenance. RBAC and audit will need to gate who can register datasets, approve them, and attach lineage—**not** defined in this phase.
