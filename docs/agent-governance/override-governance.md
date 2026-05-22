# Override governance

Overrides allow operators to **bypass** default constraints in emergencies. Without governance, overrides become invisible back doors.

## Requirements

- **Documented rationale**: text or ticket reference stored alongside the override event.
- **Approver identity**: who authorised the bypass and under which policy article.
- **Break-glass discipline**: `emergency_break_glass_used` should be rare; post-incident reviews mandatory when set.

## Snapshot signals

`override_events_observed`, `undocumented_override_events`, and `emergency_break_glass_used` feed deterministic scoring. Undocumented overrides carry the heaviest penalties in the shipped heuristic.

## Relationship to GovAI verdicts

This documentation describes **organisational** override process. It does not redefine GovAI `VALID`, `INVALID`, or `BLOCKED` semantics for hosted audit services.
