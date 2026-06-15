//! Zip bundle manifest and canonical digest for offline signed audit export packs.

use crate::canonical_json::{canonical_json_bytes, sha256_hex_bytes, sort_json_value};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::io::{Read, Write};

pub const BUNDLE_SCHEMA_V1: &str = "aigov.audit_export_bundle.v1";
pub const DEFAULT_MANIFEST_PATH: &str = "manifest.json";
pub const DEFAULT_AUDIT_EXPORT_PATH: &str = "audit_export.json";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BundleFileEntry {
    pub path: String,
    pub sha256: String,
    #[serde(default = "default_true")]
    pub required: bool,
    #[serde(default)]
    pub unsigned: bool,
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct EvidenceRef {
    pub ref_id: String,
    pub path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FindingRef {
    pub finding_id: String,
    pub path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct UnsignedDependency {
    pub ref_id: String,
    pub path: String,
    #[serde(default)]
    pub required_for_explanation: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AuditExportBundleManifest {
    pub schema_version: String,
    pub run_id: String,
    pub audit_export_path: String,
    pub files: Vec<BundleFileEntry>,
    #[serde(default)]
    pub evidence_refs: Vec<EvidenceRef>,
    #[serde(default)]
    pub finding_refs: Vec<FindingRef>,
    #[serde(default)]
    pub unsigned_dependencies: Vec<UnsignedDependency>,
    pub canonical_bundle_digest_sha256: String,
}

pub fn sha256_content_hex(content: &[u8]) -> String {
    sha256_hex_bytes(content)
}

pub fn manifest_for_digest(manifest: &AuditExportBundleManifest) -> Value {
    let mut v = serde_json::to_value(manifest).expect("manifest serde");
    if let Some(obj) = v.as_object_mut() {
        obj.remove("canonical_bundle_digest_sha256");
        if let Some(files) = obj.get_mut("files").and_then(|f| f.as_array_mut()) {
            files.sort_by(|a, b| {
                let pa = a.get("path").and_then(|p| p.as_str()).unwrap_or("");
                let pb = b.get("path").and_then(|p| p.as_str()).unwrap_or("");
                pa.cmp(pb)
            });
        }
    }
    sort_json_value(v)
}

pub fn compute_canonical_bundle_digest(manifest: &AuditExportBundleManifest) -> String {
    let canonical = manifest_for_digest(manifest);
    sha256_hex_bytes(&canonical_json_bytes(&canonical))
}

pub fn finalize_manifest_digest(mut manifest: AuditExportBundleManifest) -> AuditExportBundleManifest {
    manifest.canonical_bundle_digest_sha256 = compute_canonical_bundle_digest(&manifest);
    manifest
}

pub fn read_zip_entries(zip_bytes: &[u8]) -> Result<BTreeMap<String, Vec<u8>>, String> {
    let cursor = std::io::Cursor::new(zip_bytes);
    let mut archive =
        zip::ZipArchive::new(cursor).map_err(|e| format!("invalid zip bundle: {e}"))?;
    let mut out: BTreeMap<String, Vec<u8>> = BTreeMap::new();
    for i in 0..archive.len() {
        let mut file = archive
            .by_index(i)
            .map_err(|e| format!("zip entry {i}: {e}"))?;
        let name = normalize_zip_path(file.name());
        if name.is_empty() {
            continue;
        }
        let mut buf = Vec::new();
        file.read_to_end(&mut buf)
            .map_err(|e| format!("read zip entry {name}: {e}"))?;
        out.insert(name, buf);
    }
    Ok(out)
}

pub fn write_zip_entries(entries: &BTreeMap<String, Vec<u8>>) -> Result<Vec<u8>, String> {
    let mut buf = Vec::new();
    {
        let mut zip = zip::ZipWriter::new(std::io::Cursor::new(&mut buf));
        let options = zip::write::SimpleFileOptions::default()
            .compression_method(zip::CompressionMethod::Stored);
        for (path, content) in entries {
            zip.start_file(path, options)
                .map_err(|e| format!("zip start {path}: {e}"))?;
            zip.write_all(content)
                .map_err(|e| format!("zip write {path}: {e}"))?;
        }
        zip.finish().map_err(|e| format!("zip finish: {e}"))?;
    }
    Ok(buf)
}

fn normalize_zip_path(path: &str) -> String {
    path.trim_start_matches("./").replace('\\', "/")
}

pub fn parse_manifest_bytes(bytes: &[u8]) -> Result<AuditExportBundleManifest, String> {
    serde_json::from_slice(bytes).map_err(|e| format!("manifest json parse error: {e}"))
}

pub fn build_manifest_json(manifest: &AuditExportBundleManifest) -> Result<Vec<u8>, String> {
    let sorted = sort_json_value(serde_json::to_value(manifest).map_err(|e| e.to_string())?);
    serde_json::to_vec_pretty(&sorted).map_err(|e| e.to_string())
}

pub fn manifest_from_parts(
    run_id: &str,
    audit_export_path: &str,
    files: Vec<BundleFileEntry>,
    evidence_refs: Vec<EvidenceRef>,
    finding_refs: Vec<FindingRef>,
    unsigned_dependencies: Vec<UnsignedDependency>,
) -> AuditExportBundleManifest {
    finalize_manifest_digest(AuditExportBundleManifest {
        schema_version: BUNDLE_SCHEMA_V1.to_string(),
        run_id: run_id.to_string(),
        audit_export_path: audit_export_path.to_string(),
        files,
        evidence_refs,
        finding_refs,
        unsigned_dependencies,
        canonical_bundle_digest_sha256: String::new(),
    })
}

#[cfg(test)]
pub fn build_test_zip(entries: BTreeMap<String, Vec<u8>>) -> Vec<u8> {
    write_zip_entries(&entries).expect("zip")
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn canonical_digest_stable_across_key_order() {
        let files = vec![BundleFileEntry {
            path: "audit_export.json".to_string(),
            sha256: "c".repeat(64),
            required: true,
            unsigned: false,
        }];
        let m1 = finalize_manifest_digest(AuditExportBundleManifest {
            schema_version: BUNDLE_SCHEMA_V1.to_string(),
            run_id: "run-1".to_string(),
            audit_export_path: "audit_export.json".to_string(),
            files: files.clone(),
            evidence_refs: vec![],
            finding_refs: vec![],
            unsigned_dependencies: vec![],
            canonical_bundle_digest_sha256: String::new(),
        });
        let digest1 = m1.canonical_bundle_digest_sha256.clone();

        let raw = json!({
            "run_id": "run-1",
            "files": [{"path":"audit_export.json","sha256":"c".repeat(64),"required":true,"unsigned":false}],
            "schema_version": BUNDLE_SCHEMA_V1,
            "audit_export_path": "audit_export.json",
            "evidence_refs": [],
            "finding_refs": [],
            "unsigned_dependencies": [],
            "canonical_bundle_digest_sha256": digest1,
        });
        let parsed: AuditExportBundleManifest =
            serde_json::from_value(raw).expect("parse reordered manifest");
        assert_eq!(digest1, compute_canonical_bundle_digest(&parsed));
    }

    #[test]
    fn canonical_digest_changes_when_content_changes() {
        let base = manifest_from_parts("run-1", "audit_export.json", vec![BundleFileEntry {
            path: "audit_export.json".to_string(),
            sha256: "a".repeat(64),
            required: true,
            unsigned: false,
        }], vec![], vec![], vec![]);
        let mut tampered = base.clone();
        tampered.files[0].sha256 = "b".repeat(64);
        tampered.canonical_bundle_digest_sha256 = compute_canonical_bundle_digest(&tampered);
        assert_ne!(
            base.canonical_bundle_digest_sha256,
            tampered.canonical_bundle_digest_sha256
        );
    }
}
