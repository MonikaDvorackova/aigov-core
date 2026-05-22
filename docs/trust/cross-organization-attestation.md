# Cross-organization attestation

Suppliers, auditors, and parent organisations sometimes need to **attest** to artefacts produced in another security boundary (for example a vendor signing an evidence pack your tenant ingests).

## Model

- Each organisation maintains its own **trust anchors** and **signing profiles** (see `trust/trust-chain-example.json`).
- Cross-boundary trust is established through **explicit credential exchange**: certificate paths, signed federation metadata, or contractual key registers—not implicit trust in filenames.

## Attestation bundle

`trust/attestation-bundle-example.json` shows how to bind:

- A digest of the attested artefact,
- One or more signatures with `algorithm_id` and `kid`,
- References to a `trust_chain_id` and `signing_profile_id`.

Downstream consumers must validate **both** the cryptographic chain **and** business authorisation (contracts, data-processing agreements).

## EU AI Act and procurement context

Map attestations to your **AI system documentation** and vendor risk processes. GovAI provides evidence and verdict interfaces; cross-org attestation is a **trust transport** layer on top.
