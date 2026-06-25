//! Derived epistemic readiness for governance eligibility reconstruction.
//!
//! Computed from audit export + replay validation only — never stored in the ledger.

use crate::policy_config::PolicyConfig;
use crate::replay_engine::replay_audit_export_v1;
use crate::replay_validation::EXPORT_SCHEMA_V1;
use crate::trace_verification_plan::{
    build_trace_verification_plan_from_readiness, trace_verification_plan_to_json,
};
use serde::Serialize;
use serde_json::{json, Value};

pub const EPISTEMIC_READINESS_SCHEMA_V1: &str = "aigov.epistemic_readiness.v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EpistemicReadinessStatus {
    Ready,
    Partial,
    NotReady,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct KnowledgeRequirement {
    pub code: String,
    pub category: String,
    pub satisfied: bool,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct KnowledgeCoverage {
    pub satisfied_count: usize,
    pub total_count: usize,
    /// Deterministic fraction string, e.g. `"7/7"`.
    pub ratio: String,
    pub missing_requirement_codes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct EpistemicTraceClaim {
    /// Stable identifier for the claim within the export evaluation.
    pub claim_id: String,
    /// Human-readable statement of what is known about the run.
    pub statement: String,
    /// Provenance pointer: event_id, export field path, or replay projection.
    pub source: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct KnowledgeContinuity {
    pub chain_continuous: bool,
    pub events_digest_continuous: bool,
    pub policy_reference_present: bool,
    pub policy_artifact_retrievable: bool,
    pub lineage_resolved: bool,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct ReconstructionConfidence {
    /// `high` | `medium` | `low` | `none`
    pub level: String,
    /// Deterministic score fraction, e.g. `"6/8"`.
    pub score: String,
    /// Always true — confidence is advisory, not ledger-authoritative.
    pub non_authoritative: bool,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct KnowledgeContinuityValidation {
    pub valid: bool,
    pub failures: Vec<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct EpistemicGap {
    pub code: String,
    pub category: String,
    /// `blocking` | `advisory`
    pub severity: String,
    pub detail: String,
    pub remediation: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct EpistemicGapReport {
    pub schema_version: String,
    pub gaps: Vec<EpistemicGap>,
    pub gap_count: usize,
    pub blocking_count: usize,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct DecisionKnowledge {
    pub run_id: String,
    pub policy_version: Option<String>,
    pub exported_verdict: Option<String>,
    pub reconstructed_verdict: String,
    pub evidence_event_count: usize,
    pub determinism_digest: String,
    /// Facts asserted directly in the export carrier.
    pub known: Vec<EpistemicTraceClaim>,
    /// Claims backed by hash-chained evidence events.
    pub evidenced: Vec<EpistemicTraceClaim>,
    /// Conclusions derived by deterministic replay projection.
    pub inferred: Vec<EpistemicTraceClaim>,
    /// Drift or mismatch between export claims and replay reconstruction.
    pub changed: Vec<EpistemicTraceClaim>,
    /// Claims that cannot be independently verified from retained artifacts.
    pub unverifiable: Vec<EpistemicTraceClaim>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct EpistemicReadiness {
    pub schema_version: String,
    pub status: EpistemicReadinessStatus,
    /// Export claims `VALID` and replay reproduces the same verdict.
    pub compliance_verdict_valid: bool,
    /// Replay integrity checks pass and verdict can be re-derived.
    pub reconstructable: bool,
    /// Sorted gap codes blocking full epistemic readiness.
    pub readiness_gaps: Vec<String>,
    pub decision_knowledge: DecisionKnowledge,
    pub coverage: KnowledgeCoverage,
    pub continuity: KnowledgeContinuity,
    pub confidence: ReconstructionConfidence,
    pub replay_ok: bool,
    pub gap_report: EpistemicGapReport,
    pub continuity_validation: KnowledgeContinuityValidation,
    /// Derived trace verification plan for external audit review.
    pub trace_verification_plan: Value,
}

/// Optional signals from bundle verification (offline export bundle checks).
#[derive(Debug, Clone, Default)]
pub struct BundleVerificationSignals {
    pub unsigned_dependency_required: bool,
    pub missing_evidence_reference: bool,
    pub unsupported_bundle_schema: bool,
}

#[derive(Debug, Clone)]
pub struct EpistemicReadinessOptions<'a> {
    pub policy_cfg: &'a PolicyConfig,
    /// When `Some(false)`, policy bytes are not retrievable (archived policy loss).
    /// When `Some(true)`, policy artifact is available for `π`.
    /// When `None`, defaults to conservative `false` for offline evaluation.
    pub policy_artifact_available: Option<bool>,
    pub bundle_verification: Option<BundleVerificationSignals>,
}

impl<'a> EpistemicReadinessOptions<'a> {
    pub fn for_export_time(policy_cfg: &'a PolicyConfig) -> Self {
        Self {
            policy_cfg,
            policy_artifact_available: Some(true),
            bundle_verification: None,
        }
    }

    pub fn offline(policy_cfg: &'a PolicyConfig) -> Self {
        Self {
            policy_cfg,
            policy_artifact_available: None,
            bundle_verification: None,
        }
    }
}

pub fn evaluate_epistemic_readiness_from_export(
    export: &Value,
    opts: &EpistemicReadinessOptions<'_>,
) -> EpistemicReadiness {
    let replay = replay_audit_export_v1(export, opts.policy_cfg);
    let requirements = build_requirements(export, &replay, opts);
    let coverage = coverage_from_requirements(&requirements);
    let continuity = continuity_from_requirements(&requirements);
    let gaps = gaps_from_requirements(&requirements);
    let compliance_verdict_valid = replay
        .exported_verdict
        .as_deref()
        .map(|v| v == "VALID")
        .unwrap_or(false)
        && replay.integrity.verdict_match
        && replay.ok;
    let reconstructable = replay.ok;
    let status = derive_status(reconstructable, compliance_verdict_valid, &gaps);
    let confidence = derive_confidence(&requirements, reconstructable, &gaps);

    let policy_version = export
        .get("policy_version")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .filter(|s| !s.is_empty());

    let trace_slices = build_decision_knowledge_trace(export, &replay, opts);
    let gap_report = gap_report_from_requirements(&requirements);
    let continuity_validation = validate_knowledge_continuity(&continuity);

    let decision_knowledge = DecisionKnowledge {
        run_id: replay.run_id.clone(),
        policy_version: policy_version.clone(),
        exported_verdict: replay.exported_verdict.clone(),
        reconstructed_verdict: replay.reconstructed_verdict.clone(),
        evidence_event_count: replay.event_count,
        determinism_digest: replay.determinism_digest.clone(),
        known: trace_slices.known,
        evidenced: trace_slices.evidenced,
        inferred: trace_slices.inferred,
        changed: trace_slices.changed,
        unverifiable: trace_slices.unverifiable,
    };

    let mut readiness = EpistemicReadiness {
        schema_version: EPISTEMIC_READINESS_SCHEMA_V1.to_string(),
        status,
        compliance_verdict_valid,
        reconstructable,
        readiness_gaps: gaps,
        decision_knowledge,
        coverage,
        continuity,
        confidence,
        replay_ok: replay.ok,
        gap_report,
        continuity_validation,
        trace_verification_plan: json!({}),
    };
    let trace_plan =
        build_trace_verification_plan_from_readiness(export, &readiness, &requirements);
    readiness.trace_verification_plan = trace_verification_plan_to_json(&trace_plan);
    readiness
}

pub fn epistemic_readiness_to_json(report: &EpistemicReadiness) -> Value {
    serde_json::to_value(report).expect("EpistemicReadiness serializes")
}

pub fn evaluate_epistemic_readiness_json(
    export_json: &str,
    opts: &EpistemicReadinessOptions<'_>,
) -> Result<EpistemicReadiness, String> {
    let export: Value =
        serde_json::from_str(export_json).map_err(|e| format!("parse export json: {e}"))?;
    Ok(evaluate_epistemic_readiness_from_export(&export, opts))
}

fn build_requirements(
    export: &Value,
    replay: &crate::replay_engine::ReplayResult,
    opts: &EpistemicReadinessOptions<'_>,
) -> Vec<KnowledgeRequirement> {
    let schema_ok = export
        .get("schema_version")
        .and_then(|v| v.as_str())
        .map(|s| s == EXPORT_SCHEMA_V1)
        .unwrap_or(false);

    let policy_ref = export
        .get("policy_version")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let policy_artifact = opts.policy_artifact_available.unwrap_or(false);

    let lineage_resolved = lineage_resolved_from_export(export, replay);

    let replay_validation_ok = replay.validation.is_ok();
    let chain_ok = replay.validation.chain_continuity_ok;
    let digest_ok = replay.validation.events_content_sha256_ok;

    let coverage_complete = replay
        .projection
        .as_ref()
        .map(|p| p.current_state.requirements.missing.is_empty())
        .unwrap_or(false);

    let policy_version_drift = policy_version_drift_detected(export);
    let model_artifact_drift = model_artifact_digests(export)
        .map(|(trained, promoted)| trained != promoted)
        .unwrap_or(false);

    let mut reqs = vec![
        req(
            "unsupported_schema_version",
            "schema",
            schema_ok,
            if schema_ok {
                "export schema_version is supported"
            } else {
                "export schema_version is not aigov.audit_export.v1"
            },
        ),
        req(
            "replay_validation_failure",
            "replay",
            replay_validation_ok,
            if replay_validation_ok {
                "replay validation passed"
            } else {
                "replay validation reported errors"
            },
        ),
        req(
            "compliance_verdict_reconstructable",
            "replay",
            replay.ok,
            if replay.ok {
                "exported verdict matches replayed governance projection"
            } else {
                "verdict or integrity could not be reconstructed from export"
            },
        ),
        req(
            "chain_continuous",
            "continuity",
            chain_ok,
            if chain_ok {
                "hash chain continuity validated"
            } else {
                "hash chain continuity failed"
            },
        ),
        req(
            "events_digest_continuous",
            "continuity",
            digest_ok,
            if digest_ok {
                "events_content_sha256 matches evidence_events"
            } else {
                "events_content_sha256 mismatch"
            },
        ),
        req(
            "missing_policy_reference",
            "policy",
            policy_ref,
            if policy_ref {
                "policy_version reference present in export"
            } else {
                "policy_version missing from export"
            },
        ),
        req(
            "missing_policy_artifact",
            "policy",
            policy_artifact,
            if policy_artifact {
                "policy artifact retrievable for replay rule set"
            } else {
                "policy artifact not available for years-later reconstruction"
            },
        ),
        req(
            "unresolved_lineage",
            "lineage",
            lineage_resolved,
            if lineage_resolved {
                "delegation lineage resolved"
            } else {
                "delegation lineage unresolved or degraded"
            },
        ),
        req(
            "knowledge_coverage_complete",
            "coverage",
            coverage_complete,
            if coverage_complete {
                "no missing evidence requirements in governance projection"
            } else {
                "governance projection reports missing evidence"
            },
        ),
        req(
            "policy_version_drift",
            "policy",
            !policy_version_drift,
            if policy_version_drift {
                "export policy_version fields disagree across carrier sections"
            } else {
                "policy_version consistent across export carrier"
            },
        ),
        req(
            "model_artifact_drift",
            "model",
            !model_artifact_drift,
            if model_artifact_drift {
                "model_trained and model_promoted artifact digests differ"
            } else {
                "model artifact digest consistent across train and promote"
            },
        ),
    ];

    if let Some(bundle) = &opts.bundle_verification {
        reqs.push(req(
            "unsigned_dependency",
            "bundle",
            !bundle.unsigned_dependency_required,
            if bundle.unsigned_dependency_required {
                "required dependency lacks signature"
            } else {
                "no unsigned required dependency detected"
            },
        ));
        reqs.push(req(
            "missing_evidence_reference",
            "bundle",
            !bundle.missing_evidence_reference,
            if bundle.missing_evidence_reference {
                "bundle references evidence not present in export"
            } else {
                "evidence references resolvable in export"
            },
        ));
        if bundle.unsupported_bundle_schema {
            reqs.push(req(
                "unsupported_schema_version",
                "bundle",
                false,
                "bundle schema version unsupported",
            ));
        }
    }

    reqs.sort_by(|a, b| a.code.cmp(&b.code));
    reqs
}

fn req(code: &str, category: &str, satisfied: bool, detail: &str) -> KnowledgeRequirement {
    KnowledgeRequirement {
        code: code.to_string(),
        category: category.to_string(),
        satisfied,
        detail: detail.to_string(),
    }
}

fn coverage_from_requirements(requirements: &[KnowledgeRequirement]) -> KnowledgeCoverage {
    let total = requirements.len();
    let satisfied_count = requirements.iter().filter(|r| r.satisfied).count();
    let mut missing: Vec<String> = requirements
        .iter()
        .filter(|r| !r.satisfied)
        .map(|r| r.code.clone())
        .collect();
    missing.sort();
    missing.dedup();
    KnowledgeCoverage {
        satisfied_count,
        total_count: total,
        ratio: format!("{satisfied_count}/{total}"),
        missing_requirement_codes: missing,
    }
}

fn continuity_from_requirements(requirements: &[KnowledgeRequirement]) -> KnowledgeContinuity {
    let satisfied = |code: &str| {
        requirements
            .iter()
            .find(|r| r.code == code)
            .map(|r| r.satisfied)
            .unwrap_or(false)
    };
    KnowledgeContinuity {
        chain_continuous: satisfied("chain_continuous"),
        events_digest_continuous: satisfied("events_digest_continuous"),
        policy_reference_present: satisfied("missing_policy_reference"),
        policy_artifact_retrievable: satisfied("missing_policy_artifact"),
        lineage_resolved: satisfied("unresolved_lineage"),
    }
}

fn gaps_from_requirements(requirements: &[KnowledgeRequirement]) -> Vec<String> {
    let mut gaps: Vec<String> = requirements
        .iter()
        .filter(|r| !r.satisfied)
        .map(|r| r.code.clone())
        .collect();
    gaps.sort();
    gaps.dedup();
    gaps
}

struct DecisionKnowledgeTraceSlices {
    known: Vec<EpistemicTraceClaim>,
    evidenced: Vec<EpistemicTraceClaim>,
    inferred: Vec<EpistemicTraceClaim>,
    changed: Vec<EpistemicTraceClaim>,
    unverifiable: Vec<EpistemicTraceClaim>,
}

fn trace_claim(claim_id: &str, statement: &str, source: &str) -> EpistemicTraceClaim {
    EpistemicTraceClaim {
        claim_id: claim_id.to_string(),
        statement: statement.to_string(),
        source: source.to_string(),
    }
}

pub fn validate_knowledge_continuity(continuity: &KnowledgeContinuity) -> KnowledgeContinuityValidation {
    let mut failures = Vec::new();
    if !continuity.chain_continuous {
        failures.push("hash chain continuity failed".to_string());
    }
    if !continuity.events_digest_continuous {
        failures.push("events_content_sha256 mismatch".to_string());
    }
    if !continuity.policy_reference_present {
        failures.push("policy_version reference missing".to_string());
    }
    if !continuity.policy_artifact_retrievable {
        failures.push("policy artifact not retrievable".to_string());
    }
    if !continuity.lineage_resolved {
        failures.push("delegation lineage unresolved".to_string());
    }
    failures.sort();
    KnowledgeContinuityValidation {
        valid: failures.is_empty(),
        failures,
    }
}

fn gap_severity(code: &str, category: &str) -> &'static str {
    match code {
        "missing_policy_artifact" | "knowledge_coverage_complete" => "advisory",
        _ if category == "coverage" => "advisory",
        _ => "blocking",
    }
}

fn gap_remediation(code: &str) -> &'static str {
    match code {
        "unsupported_schema_version" => "Re-export using supported aigov.audit_export.v1 schema.",
        "replay_validation_failure" | "events_digest_continuous" | "chain_continuous" => {
            "Restore tamper-evident ledger chain or re-export from authoritative log."
        }
        "compliance_verdict_reconstructable" => {
            "Reconcile export verdict with replayed governance projection."
        }
        "missing_policy_reference" => "Include policy_version in export metadata.",
        "missing_policy_artifact" => "Archive policy bytes or digest with export for years-later replay.",
        "unresolved_lineage" => "Resolve delegation lineage or document orphaned runs.",
        "missing_evidence_reference" => "Bind bundle evidence references to export events.",
        "unsigned_dependency" => "Sign required dependencies or record waiver under policy.",
        "knowledge_coverage_complete" => "Supply missing evidence events required by policy.",
        "model_artifact_drift" => "Align model_trained and model_promoted artifact digests.",
        "policy_version_drift" => "Align export policy_version fields across carrier sections.",
        _ => "Review requirement detail and close the epistemic gap.",
    }
}

pub fn gap_report_from_requirements(requirements: &[KnowledgeRequirement]) -> EpistemicGapReport {
    let mut gaps: Vec<EpistemicGap> = requirements
        .iter()
        .filter(|r| !r.satisfied)
        .map(|r| EpistemicGap {
            code: r.code.clone(),
            category: r.category.clone(),
            severity: gap_severity(&r.code, &r.category).to_string(),
            detail: r.detail.clone(),
            remediation: gap_remediation(&r.code).to_string(),
        })
        .collect();
    gaps.sort_by(|a, b| a.code.cmp(&b.code));
    let blocking_count = gaps.iter().filter(|g| g.severity == "blocking").count();
    EpistemicGapReport {
        schema_version: "aigov.epistemic_gap_report.v1".to_string(),
        gap_count: gaps.len(),
        blocking_count,
        gaps,
    }
}

fn build_decision_knowledge_trace(
    export: &Value,
    replay: &crate::replay_engine::ReplayResult,
    opts: &EpistemicReadinessOptions<'_>,
) -> DecisionKnowledgeTraceSlices {
    let mut known = Vec::new();
    let mut evidenced = Vec::new();
    let mut inferred = Vec::new();
    let mut changed = Vec::new();
    let mut unverifiable = Vec::new();

    known.push(trace_claim(
        "known.run_id",
        &format!("run_id is {}", replay.run_id),
        "export.run.run_id",
    ));
    if let Some(schema) = export.get("schema_version").and_then(|v| v.as_str()) {
        known.push(trace_claim(
            "known.schema_version",
            &format!("export schema_version is {schema}"),
            "export.schema_version",
        ));
    }
    if let Some(pv) = export.get("policy_version").and_then(|v| v.as_str()) {
        known.push(trace_claim(
            "known.policy_version",
            &format!("export policy_version is {pv}"),
            "export.policy_version",
        ));
    }
    if let Some(verdict) = replay.exported_verdict.as_deref() {
        known.push(trace_claim(
            "known.exported_verdict",
            &format!("export decision.verdict is {verdict}"),
            "export.decision.verdict",
        ));
    }

    if let Some(events) = export.get("evidence_events").and_then(|v| v.as_array()) {
        for (i, ev) in events.iter().enumerate() {
            let event_id = ev
                .get("event_id")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown");
            let event_type = ev
                .get("event_type")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown");
            evidenced.push(trace_claim(
                &format!("evidenced.event.{i}"),
                &format!("evidence event {event_type} recorded"),
                &format!("export.evidence_events[{event_id}]"),
            ));
        }
    }
    if let Some(digest) = export
        .get("evidence_hashes")
        .and_then(|h| h.get("events_content_sha256"))
        .and_then(|v| v.as_str())
    {
        evidenced.push(trace_claim(
            "evidenced.events_digest",
            &format!("events_content_sha256 is {digest}"),
            "export.evidence_hashes.events_content_sha256",
        ));
    }

    inferred.push(trace_claim(
        "inferred.reconstructed_verdict",
        &format!(
            "replay reconstructed verdict {}",
            replay.reconstructed_verdict
        ),
        "replay_engine.projection",
    ));
    inferred.push(trace_claim(
        "inferred.replay_ok",
        &format!("replay integrity ok={}", replay.ok),
        "replay_engine.integrity",
    ));
    if let Some(projection) = &replay.projection {
        inferred.push(trace_claim(
            "inferred.missing_evidence",
            &format!(
                "projection missing evidence count {}",
                projection.current_state.requirements.missing.len()
            ),
            "replay_engine.projection.requirements.missing",
        ));
    }

    if let (Some(exported), reconstructed) = (
        replay.exported_verdict.as_deref(),
        replay.reconstructed_verdict.as_str(),
    ) {
        if exported != reconstructed {
            changed.push(trace_claim(
                "changed.replay_verdict_mismatch",
                &format!("exported verdict {exported} differs from replay {reconstructed}"),
                "replay_engine.integrity.verdict_match",
            ));
        }
    }
    if let (Some(top), Some(run_pv)) = (
        export.get("policy_version").and_then(|v| v.as_str()),
        export
            .get("run")
            .and_then(|r| r.get("policy_version"))
            .and_then(|v| v.as_str()),
    ) {
        if top != run_pv {
            changed.push(trace_claim(
                "changed.policy_version_drift",
                &format!("top-level policy_version {top} differs from run.policy_version {run_pv}"),
                "export.policy_version vs export.run.policy_version",
            ));
        }
    }
    if let Some((trained_sha, promoted_sha)) = model_artifact_digests(export) {
        if trained_sha != promoted_sha {
            changed.push(trace_claim(
                "changed.model_artifact_drift",
                &format!("model_trained sha {trained_sha} differs from model_promoted sha {promoted_sha}"),
                "export.evidence_events.model_trained vs model_promoted",
            ));
        }
    }

    if !opts.policy_artifact_available.unwrap_or(false) {
        unverifiable.push(trace_claim(
            "unverifiable.policy_artifact",
            "policy artifact bytes are not available for independent replay rule set R",
            "policy_archive",
        ));
    }
    for path in external_artifact_paths(export) {
        unverifiable.push(trace_claim(
            "unverifiable.external_artifact",
            &format!("artifact path {path} cannot be verified from export alone"),
            "export.evidence_events.payload.artifact_path",
        ));
    }
    if !replay.ok {
        unverifiable.push(trace_claim(
            "unverifiable.replay_output",
            "replay output cannot be trusted while integrity checks fail",
            "replay_engine",
        ));
    }

    for slice in [&mut known, &mut evidenced, &mut inferred, &mut changed, &mut unverifiable] {
        slice.sort_by(|a, b| a.claim_id.cmp(&b.claim_id));
    }

    DecisionKnowledgeTraceSlices {
        known,
        evidenced,
        inferred,
        changed,
        unverifiable,
    }
}

fn policy_version_drift_detected(export: &Value) -> bool {
    match (
        export.get("policy_version").and_then(|v| v.as_str()),
        export
            .get("run")
            .and_then(|r| r.get("policy_version"))
            .and_then(|v| v.as_str()),
    ) {
        (Some(a), Some(b)) => a != b,
        _ => false,
    }
}

fn model_artifact_digests(export: &Value) -> Option<(String, String)> {
    let events = export.get("evidence_events")?.as_array()?;
    let mut trained: Option<String> = None;
    let mut promoted: Option<String> = None;
    for ev in events {
        let Some(ty) = ev.get("event_type").and_then(|v| v.as_str()) else {
            continue;
        };
        let Some(sha) = ev
            .get("payload")
            .and_then(|p| p.get("artifact_sha256"))
            .and_then(|v| v.as_str())
        else {
            continue;
        };
        match ty {
            "model_trained" => trained = Some(sha.to_string()),
            "model_promoted" => promoted = Some(sha.to_string()),
            _ => {}
        }
    }
    Some((trained?, promoted?))
}

fn external_artifact_paths(export: &Value) -> Vec<String> {
    let mut paths = Vec::new();
    if let Some(events) = export.get("evidence_events").and_then(|v| v.as_array()) {
        for ev in events {
            if let Some(path) = ev
                .get("payload")
                .and_then(|p| p.get("artifact_path"))
                .and_then(|v| v.as_str())
            {
                if path.starts_with("registry://") || path.starts_with("http://") || path.starts_with("https://") {
                    paths.push(path.to_string());
                }
            }
        }
    }
    paths.sort();
    paths.dedup();
    paths
}

fn lineage_resolved_from_export(
    export: &Value,
    replay: &crate::replay_engine::ReplayResult,
) -> bool {
    if let Some(status) = export
        .get("lineage")
        .and_then(|l| l.get("lineage_integrity_status"))
        .and_then(|v| v.as_str())
    {
        return status == "ok";
    }
    if let Some(lineage) = &replay.lineage {
        if let Some(status) = lineage.get("lineage_integrity_status").and_then(|v| v.as_str()) {
            return status == "ok";
        }
    }
    true
}

fn derive_status(
    reconstructable: bool,
    compliance_verdict_valid: bool,
    gaps: &[String],
) -> EpistemicReadinessStatus {
    if !reconstructable {
        return EpistemicReadinessStatus::NotReady;
    }
    let blocking: std::collections::HashSet<&str> = [
        "unsupported_schema_version",
        "replay_validation_failure",
        "compliance_verdict_reconstructable",
        "missing_evidence_reference",
        "unsigned_dependency",
        "unresolved_lineage",
        "model_artifact_drift",
        "policy_version_drift",
    ]
    .into_iter()
    .collect();
    if gaps.iter().any(|g| blocking.contains(g.as_str())) {
        return EpistemicReadinessStatus::NotReady;
    }
    if gaps.is_empty() && compliance_verdict_valid {
        return EpistemicReadinessStatus::Ready;
    }
    EpistemicReadinessStatus::Partial
}

fn derive_confidence(
    requirements: &[KnowledgeRequirement],
    reconstructable: bool,
    gaps: &[String],
) -> ReconstructionConfidence {
    let total = requirements.len().max(1);
    let satisfied = requirements.iter().filter(|r| r.satisfied).count();
    let score = format!("{satisfied}/{total}");
    let level = if !reconstructable {
        "none".to_string()
    } else if gaps.is_empty() {
        "high".to_string()
    } else if gaps.iter().any(|g| {
        g == "missing_policy_artifact"
            || g == "knowledge_coverage_complete"
            || g == "missing_policy_reference"
    }) {
        "medium".to_string()
    } else {
        "low".to_string()
    };
    ReconstructionConfidence {
        level,
        score,
        non_authoritative: true,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::bundle::{canonicalize_evidence_events, portable_evidence_digest_v1};
    use crate::replay_engine::replay_audit_export_v1;
    use crate::replay_validation::events_for_projection;
    use crate::schema::EvidenceEvent;
    use serde_json::json;

    fn discovery(run_id: &str, id: &str) -> Value {
        json!({
            "event_id": id,
            "event_type": "ai_discovery_reported",
            "ts_utc": "2026-01-01T00:00:01Z",
            "actor": "t",
            "system": "t",
            "run_id": run_id,
            "payload": { "openai": false, "transformers": false, "model_artifacts": false }
        })
    }

    fn golden_events(run_id: &str) -> Vec<Value> {
        vec![
            discovery(run_id, &format!("{run_id}-disc")),
            json!({
                "event_id": format!("{run_id}-data"),
                "event_type": "data_registered",
                "ts_utc": "2026-01-01T00:00:02Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "ai_system_id": "as1", "dataset_id": "ds1", "dataset": "ds",
                    "dataset_version": "v1", "dataset_fingerprint": "fp",
                    "dataset_governance_id": "dg1", "dataset_governance_commitment": "basic",
                    "source": "internal", "intended_use": "test", "limitations": "none",
                    "quality_summary": "ok", "governance_status": "registered"
                }
            }),
            json!({
                "event_id": format!("{run_id}-train"),
                "event_type": "model_trained",
                "ts_utc": "2026-01-01T00:00:02Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "model_version_id": "mv1", "ai_system_id": "as1", "dataset_id": "ds1",
                    "model_type": "test",
                    "artifact_path": "registry://test/m",
                    "artifact_sha256": "abc1234567890123456789012345678901234567890123456789012345678901234"
                }
            }),
            json!({
                "event_id": format!("{run_id}-eval"),
                "event_type": "evaluation_reported",
                "ts_utc": "2026-01-01T00:00:03Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "ai_system_id": "as1", "dataset_id": "ds1", "model_version_id": "mv1",
                    "metric": "accuracy", "value": 0.95, "threshold": 0.8, "passed": true
                }
            }),
            json!({
                "event_id": format!("{run_id}-risk"),
                "event_type": "risk_recorded",
                "ts_utc": "2026-01-01T00:00:04Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "assessment_id": "a1", "ai_system_id": "as1", "dataset_id": "ds1",
                    "model_version_id": "mv1", "risk_id": "r1", "risk_class": "high",
                    "severity": 4.0, "likelihood": 0.3, "status": "submitted",
                    "mitigation": "m", "owner": "o", "dataset_governance_commitment": "basic"
                }
            }),
            json!({
                "event_id": format!("{run_id}-review"),
                "event_type": "risk_reviewed",
                "ts_utc": "2026-01-01T00:00:05Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "assessment_id": "a1", "ai_system_id": "as1", "dataset_id": "ds1",
                    "model_version_id": "mv1", "risk_id": "r1", "decision": "approve",
                    "reviewer": "officer", "justification": "ok",
                    "dataset_governance_commitment": "basic"
                }
            }),
            json!({
                "event_id": format!("{run_id}-human"),
                "event_type": "human_approved",
                "ts_utc": "2026-01-01T00:00:06Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "scope": "model_promoted", "decision": "approve", "approver": "officer",
                    "justification": "ok", "assessment_id": "a1", "risk_id": "r1",
                    "dataset_governance_commitment": "basic",
                    "ai_system_id": "as1", "dataset_id": "ds1", "model_version_id": "mv1"
                }
            }),
            json!({
                "event_id": format!("{run_id}-promote"),
                "event_type": "model_promoted",
                "ts_utc": "2026-01-01T00:00:07Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "ai_system_id": "as1", "dataset_id": "ds1", "model_version_id": "mv1",
                    "artifact_path": "registry://test/m",
                    "artifact_sha256": "abc1234567890123456789012345678901234567890123456789012345678901234",
                    "promotion_reason": "test",
                    "approved_human_event_id": format!("{run_id}-human"),
                    "assessment_id": "a1", "risk_id": "r1",
                    "dataset_governance_commitment": "basic"
                }
            }),
        ]
    }

    fn chain_for(events: &[Value]) -> Vec<Value> {
        let mut prev: Option<String> = None;
        let mut out = Vec::new();
        for (i, ev) in events.iter().enumerate() {
            let rh = format!("{:064x}", i + 1);
            out.push(json!({
                "event_id": ev.get("event_id").and_then(|v| v.as_str()).unwrap_or(""),
                "ts_utc": ev.get("ts_utc").and_then(|v| v.as_str()).unwrap_or(""),
                "event_type": ev.get("event_type").and_then(|v| v.as_str()).unwrap_or(""),
                "prev_hash": prev,
                "record_hash": rh,
            }));
            prev = Some(rh);
        }
        out
    }

    fn build_export(
        run_id: &str,
        events: Vec<Value>,
        verdict: &str,
        chain: Vec<Value>,
        extra: Option<Value>,
    ) -> Value {
        let parsed: Vec<EvidenceEvent> = events
            .iter()
            .map(|e| serde_json::from_value(e.clone()).unwrap())
            .collect();
        let ordered = events_for_projection(&parsed);
        let events_sha = portable_evidence_digest_v1(run_id, &ordered);
        let mut evs = events;
        evs.sort_by(|a, b| {
            let ta = a.get("ts_utc").and_then(|v| v.as_str()).unwrap_or("");
            let tb = b.get("ts_utc").and_then(|v| v.as_str()).unwrap_or("");
            ta.cmp(tb)
        });
        let mut doc = json!({
            "ok": true,
            "schema_version": EXPORT_SCHEMA_V1,
            "policy_version": "test-policy-v1",
            "environment": "dev",
            "exported_at_utc": "2026-01-01T00:00:07Z",
            "run": { "run_id": run_id, "policy_version": "test-policy-v1", "log_path": "l.jsonl", "identifiers": {} },
            "evidence_hashes": {
                "bundle_sha256": "c".repeat(64),
                "events_content_sha256": events_sha,
                "log_chain": chain,
            },
            "decision": { "verdict": verdict, "blocked_reasons": [], "evaluation_passed": true },
            "evidence_events": evs,
            "lineage": {
                "lineage_integrity_status": "ok",
                "root_run_id": run_id,
            },
        });
        if let Some(patch) = extra {
            if let (Some(doc_obj), Some(patch_obj)) = (doc.as_object_mut(), patch.as_object()) {
                for (k, v) in patch_obj {
                    doc_obj.insert(k.clone(), v.clone());
                }
            }
        }
        doc
    }

    fn opts_export_time() -> PolicyConfig {
        PolicyConfig::default()
    }

    fn evaluate(export: &Value, artifact: Option<bool>) -> EpistemicReadiness {
        let cfg = opts_export_time();
        evaluate_epistemic_readiness_from_export(
            export,
            &EpistemicReadinessOptions {
                policy_cfg: &cfg,
                policy_artifact_available: artifact,
                bundle_verification: None,
            },
        )
    }

    #[test]
    fn valid_run_full_reconstructability() {
        let run_id = "epistemic-valid";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain, None);
        let r = evaluate(&export, Some(true));
        assert_eq!(r.status, EpistemicReadinessStatus::Ready);
        assert!(r.compliance_verdict_valid);
        assert!(r.reconstructable);
        assert!(r.readiness_gaps.is_empty());
        assert_eq!(r.coverage.ratio, "11/11");
    }

    #[test]
    fn compliance_valid_missing_policy_artifact() {
        let run_id = "epistemic-policy-loss";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain, None);
        let r = evaluate(&export, Some(false));
        assert!(r.compliance_verdict_valid);
        assert_eq!(r.status, EpistemicReadinessStatus::Partial);
        assert!(r.readiness_gaps.contains(&"missing_policy_artifact".to_string()));
    }

    #[test]
    fn missing_evidence_reference_signal() {
        let run_id = "epistemic-missing-evidence";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain, None);
        let cfg = opts_export_time();
        let r = evaluate_epistemic_readiness_from_export(
            &export,
            &EpistemicReadinessOptions {
                policy_cfg: &cfg,
                policy_artifact_available: Some(true),
                bundle_verification: Some(BundleVerificationSignals {
                    missing_evidence_reference: true,
                    ..Default::default()
                }),
            },
        );
        assert_eq!(r.status, EpistemicReadinessStatus::NotReady);
        assert!(r
            .readiness_gaps
            .contains(&"missing_evidence_reference".to_string()));
    }

    #[test]
    fn unresolved_lineage() {
        let run_id = "epistemic-lineage";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(
            run_id,
            events,
            "VALID",
            chain,
            Some(json!({
                "lineage": {
                    "lineage_integrity_status": "degraded",
                    "orphaned_delegated_runs": ["child-run-1"],
                }
            })),
        );
        let r = evaluate(&export, Some(true));
        assert_eq!(r.status, EpistemicReadinessStatus::NotReady);
        assert!(r.readiness_gaps.contains(&"unresolved_lineage".to_string()));
    }

    #[test]
    fn replay_validation_failure_tampered_digest() {
        let run_id = "epistemic-replay-fail";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let mut export = build_export(run_id, events, "VALID", chain, None);
        export["evidence_hashes"]["events_content_sha256"] = json!("0".repeat(64));
        let r = evaluate(&export, Some(true));
        assert!(!r.reconstructable);
        assert_eq!(r.status, EpistemicReadinessStatus::NotReady);
        assert!(r
            .readiness_gaps
            .iter()
            .any(|g| g == "replay_validation_failure" || g == "events_digest_continuous"));
    }

    #[test]
    fn unsupported_schema_version() {
        let run_id = "epistemic-schema";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let mut export = build_export(run_id, events, "VALID", chain, None);
        export["schema_version"] = json!("aigov.audit_export.v0");
        let r = evaluate(&export, Some(true));
        assert_eq!(r.status, EpistemicReadinessStatus::NotReady);
        assert!(r
            .readiness_gaps
            .contains(&"unsupported_schema_version".to_string()));
    }

    #[test]
    fn unsigned_dependency_required() {
        let run_id = "epistemic-unsigned";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain, None);
        let cfg = opts_export_time();
        let r = evaluate_epistemic_readiness_from_export(
            &export,
            &EpistemicReadinessOptions {
                policy_cfg: &cfg,
                policy_artifact_available: Some(true),
                bundle_verification: Some(BundleVerificationSignals {
                    unsigned_dependency_required: true,
                    ..Default::default()
                }),
            },
        );
        assert_eq!(r.status, EpistemicReadinessStatus::NotReady);
        assert!(r.readiness_gaps.contains(&"unsigned_dependency".to_string()));
    }

    #[test]
    fn confidence_is_non_authoritative() {
        let run_id = "epistemic-confidence";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain, None);
        let r = evaluate(&export, Some(true));
        assert!(r.confidence.non_authoritative);
        assert!(!r.confidence.level.is_empty());
    }

    #[test]
    fn deterministic_json_output() {
        let run_id = "epistemic-deterministic";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain, None);
        let cfg = opts_export_time();
        let opts = EpistemicReadinessOptions {
            policy_cfg: &cfg,
            policy_artifact_available: Some(true),
            bundle_verification: None,
        };
        let r1 = evaluate_epistemic_readiness_from_export(&export, &opts);
        let r2 = evaluate_epistemic_readiness_from_export(&export, &opts);
        let j1 = serde_json::to_string(&epistemic_readiness_to_json(&r1)).unwrap();
        let j2 = serde_json::to_string(&epistemic_readiness_to_json(&r2)).unwrap();
        assert_eq!(j1, j2);
        assert_eq!(r1, r2);
    }

    #[test]
    fn compliance_valid_not_epistemically_ready_distinct() {
        let run_id = "epistemic-distinct";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain, None);
        let r = evaluate(&export, Some(false));
        assert!(r.compliance_verdict_valid);
        assert_ne!(r.status, EpistemicReadinessStatus::Ready);
    }

    #[test]
    fn replay_projection_consistent_with_engine() {
        let run_id = "epistemic-replay-hook";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain, None);
        let replay = replay_audit_export_v1(&export, &PolicyConfig::default());
        assert!(replay.ok);
        let parsed: Vec<EvidenceEvent> = export
            .get("evidence_events")
            .and_then(|v| v.as_array())
            .unwrap()
            .iter()
            .map(|e| serde_json::from_value(e.clone()).unwrap())
            .collect();
        let canon = canonicalize_evidence_events(parsed);
        let digest = portable_evidence_digest_v1(run_id, &canon);
        assert_eq!(
            digest,
            export
                .get("evidence_hashes")
                .and_then(|h| h.get("events_content_sha256"))
                .and_then(|v| v.as_str())
                .unwrap()
        );
    }

    #[test]
    fn model_artifact_drift_detected() {
        let run_id = "epistemic-model-drift";
        let mut events = golden_events(run_id);
        events[7]["payload"]["artifact_sha256"] =
            json!("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain, None);
        let r = evaluate(&export, Some(true));
        assert!(r
            .readiness_gaps
            .contains(&"model_artifact_drift".to_string()));
        assert!(r
            .decision_knowledge
            .changed
            .iter()
            .any(|c| c.claim_id == "changed.model_artifact_drift"));
        assert!(!r.gap_report.gaps.is_empty());
    }

    #[test]
    fn policy_version_drift_detected() {
        let run_id = "epistemic-policy-drift";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let mut export = build_export(run_id, events, "VALID", chain, None);
        export["policy_version"] = json!("policy-a");
        export["run"]["policy_version"] = json!("policy-b");
        let r = evaluate(&export, Some(true));
        assert!(r
            .readiness_gaps
            .contains(&"policy_version_drift".to_string()));
        assert!(r
            .decision_knowledge
            .changed
            .iter()
            .any(|c| c.claim_id == "changed.policy_version_drift"));
    }

    #[test]
    fn unverifiable_external_artifact_paths() {
        let run_id = "epistemic-unverifiable";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain, None);
        let r = evaluate(&export, Some(false));
        assert!(r
            .decision_knowledge
            .unverifiable
            .iter()
            .any(|c| c.claim_id == "unverifiable.external_artifact"));
        assert!(r
            .decision_knowledge
            .unverifiable
            .iter()
            .any(|c| c.claim_id == "unverifiable.policy_artifact"));
    }

    #[test]
    fn replay_verdict_mismatch_surfaces_in_changed() {
        let run_id = "epistemic-replay-mismatch";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "BLOCKED", chain, None);
        let r = evaluate(&export, Some(true));
        assert!(!r.compliance_verdict_valid);
        assert!(r
            .decision_knowledge
            .changed
            .iter()
            .any(|c| c.claim_id == "changed.replay_verdict_mismatch"));
    }

    #[test]
    fn knowledge_continuity_validation_reports_failures() {
        let continuity = KnowledgeContinuity {
            chain_continuous: false,
            events_digest_continuous: true,
            policy_reference_present: true,
            policy_artifact_retrievable: false,
            lineage_resolved: true,
        };
        let validation = validate_knowledge_continuity(&continuity);
        assert!(!validation.valid);
        assert!(validation.failures.iter().any(|f| f.contains("chain")));
        assert!(validation
            .failures
            .iter()
            .any(|f| f.contains("policy artifact")));
    }

    #[test]
    fn trace_verification_plan_attached_to_readiness() {
        let run_id = "epistemic-trace-plan";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain, None);
        let r = evaluate(&export, Some(true));
        assert_eq!(
            r.trace_verification_plan
                .get("schema_version")
                .and_then(|v| v.as_str()),
            Some("govai.standards.trace_verification_plan.v1")
        );
        assert!(r
            .trace_verification_plan
            .get("plan_digest")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .starts_with("sha256:"));
    }
}
