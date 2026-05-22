# Standards — correctness properties and limits

## Canonical JSON invariants

- `canonical_json` uses UTF-8, **sorted object keys**, no insignificant whitespace, and stable list ordering as defined by each validator’s preimage construction.
- `canonical_digest` is **SHA-256** over the UTF-8 bytes of `canonical_json` for the chosen preimage, returned as `sha256:<64 hex>`.

## Digest stability

- For a fixed input document that **passes** validation, repeated validation yields the **same** digest (regression-tested in `python/tests/test_phase5_standards_integration.py` and `test_phase5_standards_evaluation.py`).
- Optional digests embedded in documents (for example `plan_digest`, `pack_digest`) must **match** the canonical preimage or validation fails (`ok=false`).

## Validator guarantees

- **Structural:** required keys, enum domains, uniqueness constraints, referential integrity within the document.
- **Safety:** banned raw payload keys (`prompt`, `content`, etc.) anywhere in the tree.
- **Graph:** delegation graph includes **directed cycle detection** on `(from_node_id → to_node_id)` edges.

## Cross-reference guarantees

- Cross-document consistency (for example `capability_id` alignment) is **not** proven automatically across arbitrary file pairs unless operators run integration tests or custom checks. Example corpus in `examples/standards/` is intentionally self-consistent.

## Fail-closed document semantics

- Load failures (missing file, parse error, unsupported extension, oversize file) produce **`ok=false`** JSON and **non-zero** exit codes without Python tracebacks on stdout.
- Schema violations produce **`ok=false`** with sorted `issues` and exit **2** (`EX_INVALID`).

## Known limitations

- Validators do not fetch or verify external URLs, keys, or signatures.
- No runtime enforcement linkage: passing validation does **not** imply `GET /compliance-summary` is `VALID`.
