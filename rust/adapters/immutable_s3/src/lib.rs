use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;

use aigov_audit::immutable_store::{
    EnterpriseImmutableS3Adapter, ImmutableBackendKind, ImmutableObjectLockMode, ImmutableStoreConfig,
};
use aws_sdk_s3::types::{ObjectLockLegalHoldStatus, ObjectLockMode};
use aws_smithy_http_client_reqwest::ReqwestHttpClient;

#[derive(Clone)]
pub struct ImmutableS3ObjectLockAdapter {
    s3: Arc<aws_sdk_s3::Client>,
}

impl ImmutableS3ObjectLockAdapter {
    pub async fn new_from_env() -> Result<Self, String> {
        let reqwest_client = reqwest::Client::builder()
            .user_agent("govai/aigov_immutable_s3")
            .build()
            .map_err(|e| format!("failed to build reqwest client: {e}"))?;

        let shared = aws_config::defaults(aws_config::BehaviorVersion::latest())
            .http_client(ReqwestHttpClient::new(reqwest_client))
            .load()
            .await;
        Ok(Self {
            s3: Arc::new(aws_sdk_s3::Client::new(&shared)),
        })
    }

    fn bucket(cfg: &ImmutableStoreConfig) -> Result<&str, String> {
        cfg.s3_bucket
            .as_deref()
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .ok_or_else(|| "missing s3 bucket".to_string())
    }

    fn mode(cfg: &ImmutableStoreConfig) -> Result<ObjectLockMode, String> {
        match cfg.resolved_object_lock_mode()? {
            ImmutableObjectLockMode::Compliance => Ok(ObjectLockMode::Compliance),
            ImmutableObjectLockMode::Governance => Ok(ObjectLockMode::Governance),
        }
    }

    fn key(cfg: &ImmutableStoreConfig, tenant_id: &str, anchor_id: &str) -> String {
        aigov_audit::immutable_store::s3_anchor_key(&cfg.s3_prefix, tenant_id, anchor_id)
    }

    fn expected_retain_until_unix_secs(cfg: &ImmutableStoreConfig) -> Result<i64, String> {
        let now = chrono::Utc::now();
        let until = now
            .checked_add_signed(chrono::Duration::days(cfg.retention_days as i64))
            .ok_or_else(|| "retention overflow".to_string())?;
        Ok(until.timestamp())
    }

    async fn write_impl(
        &self,
        cfg: &ImmutableStoreConfig,
        tenant_id: &str,
        anchor_id: &str,
        bytes: Vec<u8>,
    ) -> Result<(), String> {
        let bucket = Self::bucket(cfg)?;
        let key = Self::key(cfg, tenant_id, anchor_id);

        let retain_until = Self::expected_retain_until_unix_secs(cfg)?;
        let retain_until = aws_sdk_s3::primitives::DateTime::from_secs(retain_until);

        self.s3
            .put_object()
            .bucket(bucket)
            .key(key)
            .body(aws_sdk_s3::primitives::ByteStream::from(bytes))
            .object_lock_mode(Self::mode(cfg)?)
            .object_lock_retain_until_date(retain_until)
            .object_lock_legal_hold_status(ObjectLockLegalHoldStatus::Off)
            .content_type("application/json")
            .send()
            .await
            .map_err(|e| format!("s3 put_object failed: {e}"))?;

        Ok(())
    }

    async fn read_impl(
        &self,
        cfg: &ImmutableStoreConfig,
        tenant_id: &str,
        anchor_id: &str,
    ) -> Result<Option<Vec<u8>>, String> {
        let bucket = Self::bucket(cfg)?;
        let key = Self::key(cfg, tenant_id, anchor_id);

        let res = self.s3.get_object().bucket(bucket).key(key).send().await;
        match res {
            Ok(out) => {
                let data = out
                    .body
                    .collect()
                    .await
                    .map_err(|e| format!("s3 body read failed: {e}"))?
                    .into_bytes()
                    .to_vec();
                Ok(Some(data))
            }
            Err(err) => {
                // Deterministic: treat not-found as None; others are hard errors.
                let s = err.to_string();
                let is_not_found = s.contains("NoSuchKey") || s.contains("NotFound");
                if is_not_found {
                    Ok(None)
                } else {
                    Err(format!("s3 get_object failed: {err}"))
                }
            }
        }
    }

    async fn verify_impl(
        &self,
        cfg: &ImmutableStoreConfig,
        tenant_id: &str,
        anchor_id: &str,
    ) -> Result<(), String> {
        let bucket = Self::bucket(cfg)?;
        let key = Self::key(cfg, tenant_id, anchor_id);

        let head = self
            .s3
            .head_object()
            .bucket(bucket)
            .key(&key)
            .send()
            .await
            .map_err(|e| format!("s3 head_object failed: {e}"))?;

        let got_mode = head
            .object_lock_mode()
            .ok_or_else(|| "immutable checkpoint missing Object Lock mode metadata".to_string())?;

        let expected_mode = Self::mode(cfg)?;
        if *got_mode != expected_mode {
            return Err(format!(
                "immutable checkpoint Object Lock mode mismatch: expected {expected_mode:?} got {got_mode:?}"
            ));
        }

        let retain_until = head.object_lock_retain_until_date().ok_or_else(|| {
            "immutable checkpoint missing Object Lock retain-until-date metadata".to_string()
        })?;
        let retain_until = retain_until.secs();
        let expected_min = Self::expected_retain_until_unix_secs(cfg)?;
        // Fail-closed but allow clock skew: retain_until must not be *earlier* than now+retention-1day.
        if retain_until + 86400 < expected_min {
            return Err(format!(
                "immutable checkpoint retain-until-date too early: expected >= {expected_min}, got {retain_until}"
            ));
        }

        Ok(())
    }
}

impl EnterpriseImmutableS3Adapter for ImmutableS3ObjectLockAdapter {
    fn validate_s3_config<'a>(
        &'a self,
        cfg: &'a ImmutableStoreConfig,
    ) -> Pin<Box<dyn Future<Output = Result<(), String>> + Send + 'a>> {
        Box::pin(async move {
            if !matches!(cfg.kind, ImmutableBackendKind::AwsS3ObjectLock) {
                return Err("adapter only supports AwsS3ObjectLock".to_string());
            }
            // No network calls here; keep deterministic. OSS core already validates most fields.
            let _bucket = Self::bucket(cfg)?;
            let _mode = cfg.resolved_object_lock_mode()?;
            Ok(())
        })
    }

    fn write_immutable_checkpoint<'a>(
        &'a self,
        cfg: &'a ImmutableStoreConfig,
        tenant_id: &'a str,
        anchor_id: &'a str,
        bytes: Vec<u8>,
    ) -> Pin<Box<dyn Future<Output = Result<(), String>> + Send + 'a>> {
        Box::pin(async move { self.write_impl(cfg, tenant_id, anchor_id, bytes).await })
    }

    fn verify_immutable_checkpoint<'a>(
        &'a self,
        cfg: &'a ImmutableStoreConfig,
        tenant_id: &'a str,
        anchor_id: &'a str,
    ) -> Pin<Box<dyn Future<Output = Result<(), String>> + Send + 'a>> {
        Box::pin(async move { self.verify_impl(cfg, tenant_id, anchor_id).await })
    }

    fn read_immutable_checkpoint_bytes<'a>(
        &'a self,
        cfg: &'a ImmutableStoreConfig,
        tenant_id: &'a str,
        anchor_id: &'a str,
    ) -> Pin<Box<dyn Future<Output = Result<Option<Vec<u8>>, String>> + Send + 'a>> {
        Box::pin(async move { self.read_impl(cfg, tenant_id, anchor_id).await })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn base_cfg() -> ImmutableStoreConfig {
        ImmutableStoreConfig {
            kind: ImmutableBackendKind::AwsS3ObjectLock,
            s3_bucket: Some("bucket".to_string()),
            s3_prefix: "govai/anchors".to_string(),
            s3_region: Some("us-east-1".to_string()),
            retention_days: 365,
            object_lock_mode: "COMPLIANCE".to_string(),
            require_in_staging_prod: false,
        }
    }

    #[test]
    fn deterministic_key_generation() {
        let cfg = base_cfg();
        assert_eq!(
            ImmutableS3ObjectLockAdapter::key(&cfg, "t1", "a1"),
            "govai/anchors/t1/a1.json"
        );
    }

    #[test]
    fn config_validation_rejects_bad_mode() {
        let mut cfg = base_cfg();
        cfg.object_lock_mode = "nope".to_string();
        let err = cfg.resolved_object_lock_mode().unwrap_err();
        assert!(err.contains("GOVAI_S3_OBJECT_LOCK_MODE"), "{err}");
    }
}

