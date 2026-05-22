# GovAI System Diagram

```docs
preset: system-flow
```

```docs
preset: architecture-components
```

Developer or Runtime System
    ->
GovAI SDK / CLI
    ->
Evidence Collection
    ->
Policy Evaluation
    ->
VALID / INVALID / BLOCKED verdict

VALID
    -> allow progression

INVALID
    -> reject decision

BLOCKED
    -> fail closed

Policy Evaluation
    ->
Audit Ledger
    ->
Evidence Export
    ->
Replay Verification

AI Decision Flight Recorder (GovAI Functions 2.0)
    ->
Append-only trace events in Postgres (hash chain)
    ->
Extended governance telemetry (approvals, appeals, incidents, monitoring, seals, legal refs, certification)
    ->
Read APIs: flight-pack, executive-summary, legal-evidence-manifest, governance-scorecard
    ->
Authoritative ledger verdict still from GET /compliance-summary

Additional inputs:
- CI/CD pipelines
- Runtime Governance API
- Human approval flows
- Policy packs
