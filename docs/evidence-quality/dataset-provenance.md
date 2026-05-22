# Dataset provenance contract

A **dataset provenance snapshot** is a versioned JSON document describing identifiers, owners, upstream sources, and optional checksums. The canonical sample lives at `examples/evidence-quality/sample-dataset-provenance-snapshot.json` and is validated by `scripts/validate_dataset_provenance_snapshot.py`.

## Required concepts

- **`dataset_id`** and **`dataset_version`** identify the dataset in governance tooling.
- **`sources`** list URIs (object stores, registries, or other stable references) with a **`registered`** boolean.
- **`checksum_sha256`** is optional per source; when present it must be a 64-character lowercase hex string.

## Governance linkage

The snapshot includes a **`governance`** object with `approval_id` and `approval_timestamp_utc` so offline reports can cite an explicit approval record without touching production ledgers.
