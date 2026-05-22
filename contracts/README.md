## GovAI contracts (versioned)

This folder contains **machine-readable, versioned contract schemas** for GovAI’s governance core.

These schemas are treated as **public, stable interfaces** between:

- the Rust audit service (`aigov_audit`)
- the Python CLI (`govai`)
- CI/GitHub Actions integrations
- policy GitOps repos
- immutable audit anchoring backends

### Principles

- **Versioned**: new schemas are added as new files (e.g. `*.v2.*`) rather than mutating existing schemas.
- **Deterministic**: canonicalization rules and digest inputs are explicitly constrained by schema.
- **Fail-closed friendly**: schemas are designed to allow strict validation and stable error codes.

### Schemas

- `govai.policy.v1.schema.json`: signed declarative policy document (Phase 1 baseline)
- `govai.signature_report.v1.schema.json`: deterministic cryptographic verification output
- `govai.immutable_anchor.v1.schema.json`: immutable WORM anchor object (e.g. S3 Object Lock)

