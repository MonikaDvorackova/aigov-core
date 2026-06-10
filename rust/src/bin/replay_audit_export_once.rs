//! Offline helper: deterministic governance replay for an audit export JSON file.
//! Usage: `replay_audit_export_once <path-to-export.json>`

use aigov_audit::policy_config::PolicyConfig;
use aigov_audit::replay_engine::{replay_audit_export_json, replay_result_to_json};
use std::io::Read;

fn main() {
    let path = std::env::args()
        .nth(1)
        .unwrap_or_else(|| {
            eprintln!("usage: replay_audit_export_once <export.json>");
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
    let result = replay_audit_export_json(&txt, &PolicyConfig::default())
        .unwrap_or_else(|e| {
            eprintln!("replay failed: {e}");
            std::process::exit(1);
        });
    let out = replay_result_to_json(&result);
    println!("{}", serde_json::to_string_pretty(&out).expect("json"));
    if !result.ok {
        std::process::exit(1);
    }
}
