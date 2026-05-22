# Standards tooling — threat model (Phase 5)

This document covers **offline validators** and **document loaders** for portable governance standards (`python/aigov_py/standards/`). It does **not** replace the product-level threat model in `docs/project/threat_model.md`.

## Assets

- Validator implementations (deterministic rules, digest preimage construction).
- Local JSON/YAML files supplied by users or CI.
- Canonical digest outputs used for interchange and regression tests.

## Trust boundaries

- **Inside boundary:** in-process parsing and validation of a file path the operator explicitly passed to the CLI.
- **Outside boundary:** any remote system, hosted audit ledger, or customer runtime not invoked by these commands.

## Threat scenarios and mitigations

| Threat | Mitigation |
|--------|------------|
| **Malformed input** | `json.loads` / `yaml.safe_load` with explicit error codes; single JSON object on stdout with `ok=false`. |
| **Parser abuse / billion-laughs-style YAML** | YAML only via `safe_load`; document byte cap (`MAX_STANDARDS_DOCUMENT_BYTES`); fail-closed errors. |
| **Large document denial of service** | Hard cap on file size before parse; reject with `file_too_large`. |
| **Deep nesting / pathological structures** | Size cap + Python recursion limits; validators avoid unbounded recursion where practical. |
| **Digest confusion** | Digests are **sha256:** prefixed, canonical JSON with sorted keys; documented in `correctness.md`. |
| **Raw payload leakage** | Reject known raw-text field names anywhere in the tree (`find_raw_content_fields`). |
| **YAML safety assumptions** | No `yaml.load`; only `safe_load` when PyYAML is present. |
| **Compatibility drift** | Schema version fields per standard; validators are versioned with the codebase. |
| **False certification claims** | Validators prove **structural** conformance only — **not** legal certification or runtime safety. |
| **Validator bypass** | CLI prints exactly **one** JSON object; operators should pin package versions and verify digests in CI. |

## Non-goals

- No proof of absence of logic bugs in customer deployments.
- No cryptographic proof of model behaviour.
- No substitute for hosted artefact-bound gates (`submit-evidence-pack` + `verify-evidence-pack`).
