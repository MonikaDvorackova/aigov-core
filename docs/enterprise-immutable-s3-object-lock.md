# Enterprise immutable S3 (Object Lock)

GovAI supports an **enterprise** immutable storage backend backed by **AWS S3 Object Lock**.

## OSS vs enterprise

- **OSS (default)**: the main Rust crate (`rust/`, package `aigov_audit`) contains the immutable backend abstraction, env parsing, and fail-closed validation, but it intentionally **does not** depend on the AWS SDK.
- **Enterprise**: the real S3 Object Lock implementation lives in a separate Rust crate:
  `rust/adapters/immutable_s3` (package `aigov_immutable_s3`), with its own `Cargo.toml` and `Cargo.lock`.

This separation keeps the OSS `rust/Cargo.lock` free of the AWS SDK dependency tree so default Trivy scanning is clean.

## Security scanning

Phase 1 production hardening requirement: **both** the OSS core and the enterprise adapter must be security-clean without suppressions.

- OSS: `rust/Cargo.lock` does not include the AWS SDK tree.
- Enterprise adapter: uses a reqwest-backed Smithy HTTP client, eliminating the legacy `hyper-rustls 0.24` / `rustls 0.21` / `rustls-webpki 0.101.7` chain.

## Fail-closed behavior

If `GOVAI_IMMUTABLE_BACKEND=aws_s3_object_lock` is configured but the enterprise adapter is not wired into the running process, GovAI fails closed with:

`immutable S3 backend requires the enterprise immutable_s3 adapter`

## Building and testing the adapter

Run from repo root:

```bash
cd rust/adapters/immutable_s3
cargo test --locked
```

## Wiring into an enterprise runtime

The OSS crate defines a stable adapter boundary (`EnterpriseImmutableS3Adapter`) in `rust/src/immutable_store.rs`.

Enterprise builds should:

1. Add a dependency on `aigov_immutable_s3`.
2. Construct an adapter (e.g. `ImmutableS3ObjectLockAdapter::new_from_env()`).
3. Initialize the immutable store using `ImmutableStore::init_with_enterprise_adapter(cfg, adapter)`.

## Configuration (env vars)

The OSS config/validation lives in `ImmutableStoreConfig::from_env()` and `validate_startup()`:

- `GOVAI_IMMUTABLE_BACKEND=aws_s3_object_lock`
- `GOVAI_S3_OBJECT_LOCK_BUCKET` (required)
- `GOVAI_S3_OBJECT_LOCK_PREFIX` (default: `govai/anchors`)
- `AWS_REGION` or `GOVAI_S3_OBJECT_LOCK_REGION` (optional; depends on your AWS config chain)
- `GOVAI_S3_OBJECT_LOCK_RETENTION_DAYS` (default: `365`)
- `GOVAI_S3_OBJECT_LOCK_MODE` (`COMPLIANCE` or `GOVERNANCE`, default: `COMPLIANCE`)

