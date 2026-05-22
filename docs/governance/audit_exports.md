# Audit export planning primitives

Phase 3 M5 introduces **standalone audit export planning** types and deterministic validation for future AI Act readiness and enterprise audit bundles. This slice defines **identifiers, modes, and evidence-ref completeness signals only** — it does **not** materialize immutable packages or touch runtime enforcement.

## Scope

- **In scope**: `AuditExportMode`, `EvidenceCompletenessStatus`, `AuditExportRequest`, `TimeRange`, `ControlEvidenceRequirement`, `ControlEvidenceResult`, `validate_audit_export_request`, and `evaluate_evidence_completeness`.
- **Out of scope**: runtime enforcement wiring, HTTP APIs, database migrations, ledger writes, compliance-summary changes, immutable tarball or signed bundle generation, storage writes of export artifacts, and embedding **raw user content** anywhere in export planning structs (only opaque references and identifiers).

## Purpose

Planning structures describe **who** (`tenant_id`), **what kind of export** (`AuditExportMode`), an optional **time window** (`TimeRange`), optional **control filter** (`control_ids`), and **per-control evidence requirements** keyed by opaque `required_evidence_ref_ids`. Downstream exporters can assemble controls, reason codes, datasets, overrides, and runtime decisions onto these primitives without carrying payloads inside the planning layer.

## Export modes

| Mode                         | Intended use (planning)                                                    |
|-----------------------------|---------------------------------------------------------------------------|
| EVIDENCE_COMPLETENESS       | Bundle focuses on completeness of mandated evidence refs per control.     |
| AIACT_READINESS             | Planning slice aimed at structured AI Act–style auditor readiness packs. |
| FULL_IMMUTABLE_PACKAGE       | Marker for eventual full locked-down export (not implemented here).       |

Enumerated values constrain `AuditExportRequest.mode`; unknown or non-enum values fail validation.

## Validation rules (`validate_audit_export_request`)

1. **`tenant_id`** — required, non-empty after stripping whitespace.
2. **`mode`** — must be an `AuditExportMode` instance (`isinstance`).
3. **`time_range`** — optional; if set, **`start`** and **`end`** must both be **naive** or both **timezone-aware**, and **`start <= end`** under normal `datetime` comparison.
4. **`control_ids`** — optional; **`None`** means no filter; if provided as a tuple, it must contain **at least one** id, and **every element** must be non-empty after stripping.

Errors are returned as a **sorted tuple of stable strings** (same inputs → same ordering).

## Evidence completeness (`evaluate_evidence_completeness`)

Pure function: one `ControlEvidenceRequirement` plus a collection of **`present_evidence_ref_ids`** (opaque strings).

- **`evidence_applicable is False`** → `NOT_APPLICABLE` for that control (planning declares the control out of evidence scope).
- **`evidence_applicable is True`** and every required ref (after stripping, empty tokens dropped) is present in `present_evidence_ref_ids` → **`COMPLETE`**.
- Otherwise → **`INCOMPLETE`**.

Repeated calls with identical inputs yield identical `ControlEvidenceResult` values (**deterministic**).

Required and present refs are matched as **normalized sets**: strings stripped; empty strings discarded; order of inputs does not matter.

## Fail-safe behavior and determinism

Validators favor **explicit failure** (`tenant_id`, mode type, inconsistent time semantics, malformed control filters). Evidence evaluation never reads from the filesystem, network, or databases.

## Future runtime wiring

A future exporter will correlate **controls**, **reason codes**, **dataset governance refs**, **overrides**, and **runtime audit decisions**, then optionally sign and persist an immutable artifact. That pipeline is **not** part of Phase 3 M5.

## M7.5 audit export manifest planning

Phase 3 M7.5 adds a deterministic **manifest planning** helper in `python/aigov_py/audit_export_manifest.py`. This is pure model/helper code only:

- No HTTP/API wiring.
- No database migrations.
- No ledger writes.
- No export execution.
- No production immutable package generation.
- No runtime enforcement or runtime evaluate verdict behavior changes.

The manifest model is intentionally reference-only. `AuditExportManifest` contains `tenant_id`, `export_mode`, `generated_at`, planned `controls`, opaque `evidence_refs`, `dataset_lineage_refs`, `override_refs`, `ai_act_requirement_refs`, a `completeness_summary`, and a deterministic `manifest_digest`. The digest is computed over canonical manifest content excluding `manifest_digest` itself.

Evidence refs, dataset lineage refs, override refs, and AI Act requirement refs are opaque identifiers. The manifest does not model raw user content, prompts, dataset records, request payloads, or evidence bodies.

### Completeness semantics

- `tenant_id` is required via `AuditExportRequest` validation.
- `export_mode` must be an existing `AuditExportMode`.
- Missing required evidence refs mark the control `INCOMPLETE`.
- Controls declared not applicable remain `NOT_APPLICABLE`, even when evidence is missing.
- Same input produces the same manifest and `manifest_digest`.
- Changing evidence refs changes the canonical content and therefore the digest.

### Intended use

M7.5 gives future audit export work a stable planning object for review and tests. Actual export jobs, immutable packages, object storage writes, signatures, and audit ledger events remain future work behind separate scope approval.
