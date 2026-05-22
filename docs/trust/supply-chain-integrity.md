# Supply chain integrity

Cryptographic signing of governance artefacts is one control in a broader **supply chain** story that includes source code, CI configuration, container images, and policy packs.

## Alignment with repository gates

GovAI ships deterministic OSS checks (`make gate`, documentation link validation, registry validators). These gates detect **accidental drift** and missing artefacts; they do not replace **code signing** for binaries or **Sigstore** policies for images.

## Recommended pairing

- **Git commit signing** for policy and workflow changes.
- **SLSA-oriented** CI provenance for build artefacts that produce evidence exporters.
- **Signed evidence packs** when exporting compliance narratives to regulators.

## Registry documents

When publishing to the standards registry, treat entries as **signed documents** if your governance program requires non-repudiation. The interchange validators remain the semantic source of truth; signatures add tamper evidence in long-term archives.

See [immutable-trust-chain.md](immutable-trust-chain.md) for how layers compose.
