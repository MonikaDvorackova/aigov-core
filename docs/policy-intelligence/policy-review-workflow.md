# Policy review workflow

Structured snapshots include a `governance_process` object so offline checks can detect drift in **review cadence** and **basic governance flags**.

## Fields

- `quarterly_reviews_done_last_year` — integer count of completed governance reviews (0–12 for a rolling year model).
- `exception_process_documented` — boolean; whether exceptions to policy are documented.
- `segregation_of_duties` — boolean; whether SoD is asserted for sensitive paths (for example promotion or production access).

## Operational use

Teams should align these fields with real calendars and access-control reviews. The diagnostics script only verifies presence, schema, and wiring of documentation and tooling—not organizational truth.

## Related

- [`governance-gap-analysis.md`](governance-gap-analysis.md)
- [`governance-non-goals.md`](governance-non-goals.md)
