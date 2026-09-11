# Audit Export Verifier Fixture Contract

## Summary

This report covers a documentation-only fixture contract for the signed audit export verifier roadmap.

The change adds `docs/audit-export-verifier-fixture-contract.md`, which defines a small reviewer-facing contract for verifier fixtures before Rust implementation work begins. It documents stable reason-code candidates, stage-level verifier expectations, serialized result invariants, and a fixture matrix for successful and failed audit export verification paths.

No runtime verifier code, policy logic, cryptographic implementation, or production gate behavior changes in this PR.

## Evaluation gate

Evaluation behavior is not changed by this documentation update.

The fixture contract is intended to make future evaluation evidence more reviewable by specifying what each fixture should prove:

- which verification stage is exercised;
- which stable reason code is expected;
- which serialized result fields must remain deterministic;
- which negative path is covered;
- which paths remain intentionally unexercised until implementation support exists.

The document explicitly keeps success, warning, and failure states separate so future tests do not collapse verifier completeness, signature validity, and replay validity into one ambiguous boolean.

Local validation for this PR:

```bash
python3 scripts/gate_reports.py
git diff --check
```

## Human approval gate

Human approval semantics are not changed by this documentation update.

This fixture contract does not approve, reject, or bypass any runtime action. It gives maintainers a review checklist for future verifier fixtures and implementation alignment. Maintainer review is still required before any verifier behavior or public artifact contract is treated as accepted.

Open approval items:

- [ ] Maintainer confirms the reason-code taxonomy matches the Rust verifier roadmap.
- [ ] Maintainer confirms whether this contract should remain documentation-only or be converted into executable fixtures in a follow-up PR.
- [ ] Maintainer confirms which unimplemented reason codes should stay documented as future fixture targets.

## Changed files

| File | Role |
| --- | --- |
| `docs/audit-export-verifier-fixture-contract.md` | Fixture contract for signed audit export verifier result snapshots and reason-code coverage |
| `docs/reports/audit-export-verifier-fixture-contract.md` | Audit report for the documentation-only contract change |

## Boundaries

- No verifier implementation is added.
- No schema is made normative beyond maintainer review.
- No sample customer data, fake audit output, or generated production evidence is introduced.
- No public revenue, client, or endorsement claim is made.
