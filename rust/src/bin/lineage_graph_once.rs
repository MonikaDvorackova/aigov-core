//! Offline governance lineage graph for an audit export JSON file.
//! Usage: `lineage_graph_once [--mermaid] <export.json>`

use aigov_audit::governance_graph::{governance_graph_from_export, graph_to_mermaid};
use serde_json::Value;
use std::io::Read;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mermaid = args.iter().any(|a| a == "--mermaid");
    let path = args
        .iter()
        .find(|a| !a.starts_with('-'))
        .filter(|a| *a != &args[0])
        .cloned()
        .unwrap_or_else(|| {
            eprintln!("usage: lineage_graph_once [--mermaid] <export.json>");
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
    let export: Value = serde_json::from_str(&txt).unwrap_or_else(|e| {
        eprintln!("parse json: {e}");
        std::process::exit(1);
    });
    let doc = governance_graph_from_export(&export).unwrap_or_else(|e| {
        eprintln!("lineage graph failed: {e}");
        std::process::exit(1);
    });

    if mermaid {
        println!("{}", graph_to_mermaid(&doc));
        if !doc.graph.lineage_validation.is_ok() {
            std::process::exit(1);
        }
        return;
    }

    let out = serde_json::json!({
        "schema_version": doc.schema_version,
        "summary": doc.summary,
        "graph": doc.graph,
        "lineage_records": doc.lineage_records,
    });
    println!("{}", serde_json::to_string_pretty(&out).expect("json"));
    if !doc.graph.lineage_validation.is_ok() {
        std::process::exit(1);
    }
}
