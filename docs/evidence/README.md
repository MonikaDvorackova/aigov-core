# Evidence bundles

This directory stores machine verifiable evidence bundles exported from the governance engine.

Important
Evidence bundles are intentionally not committed to Git.

Why
Evidence bundles may include sensitive metadata and can be large. The repository stores only human readable audit reports under docs/reports. Each report contains a bundle_sha256 value that uniquely references the corresponding evidence bundle.

How to generate an evidence bundle
RUN_ID=<run_id> make bundle

This produces
docs/evidence/<run_id>.json

Storage policy
After generating the bundle, store it in external immutable storage with retention and access control. The report in docs/reports is the index entry. The bundle_sha256 is the integrity reference for audits, due diligence and litigation.
