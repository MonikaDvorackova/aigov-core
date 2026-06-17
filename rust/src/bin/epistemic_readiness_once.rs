//! Offline helper: derived epistemic readiness for an audit export JSON file.
//! Usage: `epistemic_readiness_once <path-to-export.json>`

use aigov_audit::epistemic_readiness::{
    epistemic_readiness_to_json, evaluate_epistemic_readiness_json, EpistemicReadinessOptions,
};
use aigov_audit::policy_config::PolicyConfig;
use std::io::Read;

fn main() {
    let path = std::env::args().nth(1).unwrap_or_else(|| {
        eprintln!("usage: epistemic_readiness_once <export.json>");
        std::process::exit(2);
    });
    let mut txt = String::new();
    if path == "-" {
        std::io::stdin()
            .read_to_string(&mut txt)
            .expect("read stdin");
    } else {
        txt = std::fs::read_to_string(&path).unwrap_or_else(|e| {
            eprintln!("read {path}: {e}");
            std::process::exit(1);
        });
    }
    let policy_cfg = PolicyConfig::default();
    let artifact_env = std::env::var("GOVAI_POLICY_ARTIFACT_AVAILABLE").ok();
    let policy_artifact_available = artifact_env.as_deref().map(|v| v == "1" || v.eq_ignore_ascii_case("true"));
    let report = evaluate_epistemic_readiness_json(
        &txt,
        &EpistemicReadinessOptions {
            policy_cfg: &policy_cfg,
            policy_artifact_available,
            bundle_verification: None,
        },
    )
    .unwrap_or_else(|e| {
        eprintln!("epistemic readiness failed: {e}");
        std::process::exit(1);
    });
    let out = epistemic_readiness_to_json(&report);
    println!("{}", serde_json::to_string_pretty(&out).expect("json"));
    if matches!(
        report.status,
        aigov_audit::epistemic_readiness::EpistemicReadinessStatus::NotReady
    ) {
        std::process::exit(1);
    }
}
