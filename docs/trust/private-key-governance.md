# Private key governance

Signing keys for governance artefacts must meet the same rigour as production TLS and database credentials.

## Storage

- Prefer **HSM**, **KMS**, or **managed signing** over filesystem PEM files.
- Restrict `Sign` IAM or RBAC to automation principals that cannot also deploy arbitrary policy.

## Separation of duties

- **Key custodians** rotate material; **release managers** approve what is signed; **auditors** verify without access to private keys.
- Dual control for root anchors where regulatory or internal policy requires it.

## CI integration

CI systems should call remote signing or use **ephemeral** keys only for non-production demonstration. Production evidence signing should not share keys with developer laptops.

## Incident handling

On suspected compromise: revoke affected `kid` values at the trust anchor, publish updated trust chain documents, and re-verify historical exports stored offline. See [../security/incident-response.md](../security/incident-response.md).
