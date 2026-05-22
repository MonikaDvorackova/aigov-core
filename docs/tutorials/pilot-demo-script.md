# Tutorial: Pilot demo script (45 minutes)

## Cast

- **Champion** — internal advocate.
- **GovAI operator** — runs or owns the audit deployment.
- **Security observer** — asks traceability questions.

## Act 1 — Problem (5 minutes)

1. Champion describes a recent “silent green deploy” risk without naming customers.
2. Operator shows **`GET /compliance-summary`** JSON for a **`BLOCKED`** training run (sanitised).

## Act 2 — Happy path (20 minutes)

1. Start local stack per **`README.md`** Docker Compose section (or use hosted URL).
2. Walk through **`make fail-closed-demo`** or the equivalent scripted path — expect **BLOCKED** first.
3. Show what evidence would be required to move toward **`VALID`** (narrative only if you lack approval in the demo environment).

## Act 3 — Evidence export (10 minutes)

1. Demonstrate **`GET /api/export/:run_id`** or repository export tooling.
2. Map one JSON field to a control in your pilot checklist.

## Act 4 — Q&A (10 minutes)

Use **`docs/troubleshooting.md`** as a backstop reference.

## Expected outcomes

- Audience understands **fail-closed** behaviour.
- Audience can name the three verdict states: **`VALID`**, **`INVALID`**, **`BLOCKED`**.

## Screenshot slots

- Compliance summary JSON (redacted).
- CI job showing non-zero exit when not **`VALID`**.

## Demo video checklist

- [ ] Audio describes verdict semantics without legal certification language.
- [ ] On-screen URLs use example hosts only.
- [ ] End card links to repository **`README.md`**.
