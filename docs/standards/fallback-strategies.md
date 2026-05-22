# Fallback strategies when providers refuse cooperation

When upstream providers decline to expose metadata, governance programmes need **explicit fallbacks** so `BLOCKED` or `INVALID` states are interpretable rather than silent.

## Strategy menu

1. **Contractual** — procurement requires minimum disclosure (model id, safety benchmark receipt, incident channel).
2. **Open-weights or reproducible builds** — shift to artefacts the deployer controls end-to-end.
3. **Independent evaluation** — third-party labs produce signed reports ingested as evidence.
4. **Conservative policy** — treat missing metadata as failing required evidence (fail-closed).
5. **Scoped deployment** — restrict high-risk use until metadata arrives.

## GovAI mechanism

- Policy modules express **required evidence**; missing items surface in `GET /compliance-summary` (`docs/trust-model.md`).

## Related

- `docs/standards/provider-cooperation-roadmap.md`
- `docs/security/threat-matrix.md`
