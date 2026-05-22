use serde::{Deserialize, Serialize};

use crate::govai_environment::GovaiEnvironment;

use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ImmutableBackendKind {
    Disabled,
    AwsS3ObjectLock,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ImmutableObjectLockMode {
    Compliance,
    Governance,
}

impl ImmutableObjectLockMode {
    pub fn parse(s: &str) -> Result<Self, String> {
        match s.trim().to_ascii_uppercase().as_str() {
            "COMPLIANCE" => Ok(Self::Compliance),
            "GOVERNANCE" => Ok(Self::Governance),
            other => Err(format!(
                "Invalid immutable audit configuration: refusing to start — GOVAI_S3_OBJECT_LOCK_MODE must be COMPLIANCE or GOVERNANCE (got {other:?})"
            )),
        }
    }
}

#[derive(Debug, Clone)]
pub struct ImmutableStoreConfig {
    pub kind: ImmutableBackendKind,
    pub s3_bucket: Option<String>,
    pub s3_prefix: String,
    pub s3_region: Option<String>,
    pub retention_days: u32,
    pub object_lock_mode: String,
    pub require_in_staging_prod: bool,
}

impl ImmutableStoreConfig {
    pub fn from_env() -> Result<Self, String> {
        let kind = std::env::var("GOVAI_IMMUTABLE_BACKEND")
            .ok()
            .unwrap_or_default()
            .trim()
            .to_ascii_lowercase();

        let kind = match kind.as_str() {
            "" | "off" | "disabled" => ImmutableBackendKind::Disabled,
            "aws_s3_object_lock" | "s3_object_lock" | "aws_s3" => {
                ImmutableBackendKind::AwsS3ObjectLock
            }
            other => return Err(format!("invalid GOVAI_IMMUTABLE_BACKEND={other:?}")),
        };

        let s3_bucket = std::env::var("GOVAI_S3_OBJECT_LOCK_BUCKET")
            .ok()
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty());
        let s3_prefix = std::env::var("GOVAI_S3_OBJECT_LOCK_PREFIX")
            .ok()
            .unwrap_or_else(|| "govai/anchors".to_string());
        let s3_prefix = s3_prefix.trim().trim_matches('/').to_string();

        let s3_region = std::env::var("AWS_REGION")
            .ok()
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .or_else(|| {
                std::env::var("GOVAI_S3_OBJECT_LOCK_REGION")
                    .ok()
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty())
            });

        let retention_days = std::env::var("GOVAI_S3_OBJECT_LOCK_RETENTION_DAYS")
            .ok()
            .and_then(|s| s.trim().parse::<u32>().ok())
            .unwrap_or(365);

        let object_lock_mode = std::env::var("GOVAI_S3_OBJECT_LOCK_MODE")
            .ok()
            .unwrap_or_else(|| "COMPLIANCE".to_string())
            .trim()
            .to_string();

        let require_in_staging_prod = std::env::var("GOVAI_IMMUTABLE_REQUIRED")
            .ok()
            .map(|s| {
                matches!(
                    s.trim().to_ascii_lowercase().as_str(),
                    "1" | "true" | "on" | "yes"
                )
            })
            .unwrap_or(false);

        Ok(Self {
            kind,
            s3_bucket,
            s3_prefix,
            s3_region,
            retention_days,
            object_lock_mode,
            require_in_staging_prod,
        })
    }

    pub fn validate_startup(&self, env: GovaiEnvironment) -> Result<(), String> {
        let must = self.require_in_staging_prod
            && matches!(env, GovaiEnvironment::Staging | GovaiEnvironment::Prod);
        match self.kind {
            ImmutableBackendKind::Disabled => {
                if must {
                    return Err("Invalid immutable audit configuration: refusing to start — GOVAI_IMMUTABLE_BACKEND must be set in staging/prod when GOVAI_IMMUTABLE_REQUIRED=true".to_string());
                }
                Ok(())
            }
            ImmutableBackendKind::AwsS3ObjectLock => {
                let _ = env;
                let bucket = self.s3_bucket.as_deref().unwrap_or("").trim();
                if bucket.is_empty() {
                    return Err("Invalid immutable audit configuration: refusing to start — GOVAI_S3_OBJECT_LOCK_BUCKET required when GOVAI_IMMUTABLE_BACKEND=aws_s3_object_lock".to_string());
                }
                if self.retention_days == 0 {
                    return Err(
                        "Invalid immutable audit configuration: refusing to start — retention_days must be > 0"
                            .to_string(),
                    );
                }
                let _mode = ImmutableObjectLockMode::parse(&self.object_lock_mode)?;
                Ok(())
            }
        }
    }

    pub fn resolved_object_lock_mode(&self) -> Result<ImmutableObjectLockMode, String> {
        ImmutableObjectLockMode::parse(&self.object_lock_mode)
    }
}

/// Enterprise-only adapter boundary for S3 Object Lock.
///
/// The OSS crate intentionally does **not** depend on the AWS SDK.
/// Enterprise builds are expected to provide an implementation (e.g. via the
/// `aigov_immutable_s3` crate) and wire it in at runtime using
/// [`ImmutableStore::init_with_enterprise_adapter`].
pub trait EnterpriseImmutableS3Adapter: Send + Sync {
    fn validate_s3_config<'a>(
        &'a self,
        cfg: &'a ImmutableStoreConfig,
    ) -> Pin<Box<dyn Future<Output = Result<(), String>> + Send + 'a>>;

    fn write_immutable_checkpoint<'a>(
        &'a self,
        cfg: &'a ImmutableStoreConfig,
        tenant_id: &'a str,
        anchor_id: &'a str,
        bytes: Vec<u8>,
    ) -> Pin<Box<dyn Future<Output = Result<(), String>> + Send + 'a>>;

    fn verify_immutable_checkpoint<'a>(
        &'a self,
        cfg: &'a ImmutableStoreConfig,
        tenant_id: &'a str,
        anchor_id: &'a str,
    ) -> Pin<Box<dyn Future<Output = Result<(), String>> + Send + 'a>>;

    fn read_immutable_checkpoint_bytes<'a>(
        &'a self,
        cfg: &'a ImmutableStoreConfig,
        tenant_id: &'a str,
        anchor_id: &'a str,
    ) -> Pin<Box<dyn Future<Output = Result<Option<Vec<u8>>, String>> + Send + 'a>>;
}

#[derive(Clone)]
pub struct ImmutableStore {
    cfg: ImmutableStoreConfig,
    enterprise_s3: Option<Arc<dyn EnterpriseImmutableS3Adapter>>,
}

impl std::fmt::Debug for ImmutableStore {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ImmutableStore")
            .field("kind", &self.cfg.kind)
            .field("enterprise_adapter_present", &self.enterprise_s3.is_some())
            .finish()
    }
}

impl ImmutableStore {
    pub async fn init(cfg: ImmutableStoreConfig) -> Result<Self, String> {
        match cfg.kind {
            ImmutableBackendKind::Disabled => Ok(Self {
                cfg,
                enterprise_s3: None,
            }),
            ImmutableBackendKind::AwsS3ObjectLock => {
                Err("immutable S3 backend requires the enterprise immutable_s3 adapter".to_string())
            }
        }
    }

    pub async fn init_with_enterprise_adapter(
        cfg: ImmutableStoreConfig,
        adapter: Arc<dyn EnterpriseImmutableS3Adapter>,
    ) -> Result<Self, String> {
        match cfg.kind {
            ImmutableBackendKind::Disabled => Ok(Self {
                cfg,
                enterprise_s3: None,
            }),
            ImmutableBackendKind::AwsS3ObjectLock => {
                adapter.validate_s3_config(&cfg).await?;
                Ok(Self {
                    cfg,
                    enterprise_s3: Some(adapter),
                })
            }
        }
    }

    pub fn enabled(&self) -> bool {
        !matches!(self.cfg.kind, ImmutableBackendKind::Disabled)
    }

    pub fn cfg(&self) -> &ImmutableStoreConfig {
        &self.cfg
    }

    pub fn anchor_key(&self, tenant_id: &str, anchor_id: &str) -> String {
        s3_anchor_key(&self.cfg.s3_prefix, tenant_id, anchor_id)
    }

    pub fn enterprise_adapter_present(&self) -> bool {
        self.enterprise_s3.is_some()
    }

    pub async fn put_anchor_object_locked(
        &self,
        tenant_id: &str,
        anchor_id: &str,
        bytes: Vec<u8>,
    ) -> Result<(), String> {
        match self.cfg.kind {
            ImmutableBackendKind::Disabled => Ok(()),
            ImmutableBackendKind::AwsS3ObjectLock => {
                let adapter = self.enterprise_s3.as_ref().ok_or_else(|| {
                    "immutable S3 backend requires the enterprise immutable_s3 adapter".to_string()
                })?;
                adapter
                    .write_immutable_checkpoint(&self.cfg, tenant_id, anchor_id, bytes)
                    .await
            }
        }
    }

    pub async fn get_anchor_bytes(
        &self,
        tenant_id: &str,
        anchor_id: &str,
    ) -> Result<Option<Vec<u8>>, String> {
        match self.cfg.kind {
            ImmutableBackendKind::Disabled => Ok(None),
            ImmutableBackendKind::AwsS3ObjectLock => {
                let adapter = self.enterprise_s3.as_ref().ok_or_else(|| {
                    "immutable S3 backend requires the enterprise immutable_s3 adapter".to_string()
                })?;
                adapter
                    .read_immutable_checkpoint_bytes(&self.cfg, tenant_id, anchor_id)
                    .await
            }
        }
    }
}

pub fn s3_anchor_key(prefix: &str, tenant_id: &str, anchor_id: &str) -> String {
    let p = prefix.trim().trim_matches('/');
    let t = tenant_id.trim();
    let a = anchor_id.trim();
    format!("{}/{}/{}.json", p, t, a)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn immutable_config_validation_rejects_missing_bucket_when_enabled() {
        let cfg = ImmutableStoreConfig {
            kind: ImmutableBackendKind::AwsS3ObjectLock,
            s3_bucket: None,
            s3_prefix: "p".to_string(),
            s3_region: None,
            retention_days: 365,
            object_lock_mode: "COMPLIANCE".to_string(),
            require_in_staging_prod: true,
        };
        let err = cfg
            .validate_startup(GovaiEnvironment::Prod)
            .expect_err("must error");
        assert!(err.contains("GOVAI_S3_OBJECT_LOCK_BUCKET"), "{err}");
    }

    #[test]
    fn immutable_disabled_validates_without_aws() {
        let cfg = ImmutableStoreConfig {
            kind: ImmutableBackendKind::Disabled,
            s3_bucket: None,
            s3_prefix: "p".to_string(),
            s3_region: None,
            retention_days: 365,
            object_lock_mode: "COMPLIANCE".to_string(),
            require_in_staging_prod: false,
        };
        assert!(cfg.validate_startup(GovaiEnvironment::Dev).is_ok());
    }

    #[tokio::test]
    async fn s3_backend_fails_closed_without_enterprise_adapter() {
        let cfg = ImmutableStoreConfig {
            kind: ImmutableBackendKind::AwsS3ObjectLock,
            s3_bucket: Some("b".to_string()),
            s3_prefix: "p".to_string(),
            s3_region: Some("us-east-1".to_string()),
            retention_days: 365,
            object_lock_mode: "COMPLIANCE".to_string(),
            require_in_staging_prod: false,
        };
        let err = ImmutableStore::init(cfg).await.expect_err("must error");
        assert!(
            err.contains("enterprise immutable_s3 adapter"),
            "unexpected error: {err}"
        );
    }

    #[test]
    fn anchor_key_is_deterministic() {
        assert_eq!(
            s3_anchor_key("govai/anchors/", " tenant ", " abc "),
            "govai/anchors/tenant/abc.json"
        );
    }
}
