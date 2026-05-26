//! Governance graph projection: nodes, edges, gates, lineage integrity.

use crate::lineage_projection::{project_lineage_records, sort_events_for_lineage, LineageEventRecord};
use crate::lineage_validation::{validate_lineage_records, LineageValidationReport};
use crate::schema::EvidenceEvent;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashSet;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GraphNode {
    pub id: String,
    pub kind: String,
    pub label: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GraphEdge {
    pub from: String,
    pub to: String,
    pub edge_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GovernanceGraph {
    pub run_id: String,
    pub root_run_id: String,
    pub nodes: Vec<GraphNode>,
    pub edges: Vec<GraphEdge>,
    pub delegation_types: Vec<String>,
    pub governance_gates: Vec<String>,
    pub lineage_integrity_status: String,
    pub lineage_validation: LineageValidationReport,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GovernanceGraphDocument {
    pub schema_version: String,
    pub graph: GovernanceGraph,
    pub lineage_records: Vec<LineageEventRecord>,
    pub summary: Value,
}

pub fn build_governance_graph(run_id: &str, events: &[EvidenceEvent]) -> GovernanceGraphDocument {
    let ordered = sort_events_for_lineage(events);
    let records = project_lineage_records(&ordered);
    let mut known_runs: HashSet<String> = HashSet::new();
    known_runs.insert(run_id.to_string());
    for r in &records {
        known_runs.insert(r.run_id.clone());
        if let Some(ref c) = r.child_run_id {
            known_runs.insert(c.clone());
        }
        if let Some(ref p) = r.lineage.parent_run_id {
            known_runs.insert(p.clone());
        }
    }

    let validation = validate_lineage_records(run_id, &records, &known_runs);
    let root_run_id = records
        .iter()
        .find(|r| r.run_id == run_id)
        .and_then(|r| r.lineage.root_run_id.clone())
        .unwrap_or_else(|| run_id.to_string());

    let (nodes, edges, delegation_types, governance_gates) =
        graph_nodes_edges(run_id, &ordered, &records);

    let lineage_integrity_status = if validation.is_ok() {
        "ok".to_string()
    } else if validation.delegation_cycle_detected {
        "cycle_detected".to_string()
    } else if !validation.errors.is_empty() {
        "invalid".to_string()
    } else {
        "degraded".to_string()
    };

    let graph = GovernanceGraph {
        run_id: run_id.to_string(),
        root_run_id: root_run_id.clone(),
        nodes,
        edges,
        delegation_types,
        governance_gates,
        lineage_integrity_status: lineage_integrity_status.clone(),
        lineage_validation: validation,
    };

    let summary = json!({
        "run_id": run_id,
        "root_run_id": root_run_id,
        "node_count": graph.nodes.len(),
        "edge_count": graph.edges.len(),
        "lineage_integrity_status": lineage_integrity_status,
        "orphaned_delegated_runs": graph.lineage_validation.orphaned_delegated_runs,
        "missing_parent_runs": graph.lineage_validation.missing_parent_runs,
    });

    GovernanceGraphDocument {
        schema_version: "govai.governance_graph.v1".to_string(),
        graph,
        lineage_records: records,
        summary,
    }
}

fn graph_nodes_edges(
    run_id: &str,
    events: &[EvidenceEvent],
    records: &[LineageEventRecord],
) -> (Vec<GraphNode>, Vec<GraphEdge>, Vec<String>, Vec<String>) {
    let mut nodes: Vec<GraphNode> = Vec::new();
    let mut edges: Vec<GraphEdge> = Vec::new();
    let mut delegation_types: HashSet<String> = HashSet::new();
    let mut governance_gates: HashSet<String> = HashSet::new();

    let run_node = format!("run:{run_id}");
    nodes.push(GraphNode {
        id: run_node.clone(),
        kind: "run".to_string(),
        label: format!("run {run_id}"),
        metadata: None,
    });

    let mut prev_event: Option<String> = None;
    for ev in events {
        if ev.run_id != run_id {
            continue;
        }
        let ev_node = format!("event:{}", ev.event_id);
        nodes.push(GraphNode {
            id: ev_node.clone(),
            kind: "event".to_string(),
            label: ev.event_type.clone(),
            metadata: Some(json!({ "ts_utc": ev.ts_utc })),
        });
        edges.push(GraphEdge {
            from: run_node.clone(),
            to: ev_node.clone(),
            edge_type: "contains".to_string(),
            metadata: None,
        });
        if let Some(ref p) = prev_event {
            edges.push(GraphEdge {
                from: p.clone(),
                to: ev_node.clone(),
                edge_type: "sequence".to_string(),
                metadata: None,
            });
        }
        prev_event = Some(ev_node.clone());

        let lin = ev.lineage();
        if let Some(ref agent_id) = lin.agent_id {
            let agent_node = format!("agent:{agent_id}");
            if !nodes.iter().any(|n| n.id == agent_node) {
                nodes.push(GraphNode {
                    id: agent_node.clone(),
                    kind: "agent".to_string(),
                    label: agent_id.clone(),
                    metadata: lin.agent_role.as_ref().map(|r| json!({ "role": r })),
                });
            }
            edges.push(GraphEdge {
                from: agent_node,
                to: ev_node.clone(),
                edge_type: "actor".to_string(),
                metadata: lin.delegation_reason.as_ref().map(|r| json!({ "reason": r })),
            });
        }

        match ev.event_type.as_str() {
            "human_approved" => {
                governance_gates.insert("human_approval".to_string());
                add_gate_node(&mut nodes, &mut edges, "gate:human_approval", "human approval", &ev_node);
            }
            "evaluation_reported" => {
                governance_gates.insert("evaluation".to_string());
                add_gate_node(&mut nodes, &mut edges, "gate:evaluation", "evaluation", &ev_node);
            }
            "agent_delegated" => {
                delegation_types.insert("agent_delegated".to_string());
                if let Some(ref child) = records
                    .iter()
                    .find(|r| r.event_id == ev.event_id)
                    .and_then(|r| r.child_run_id.clone())
                {
                    let child_node = format!("run:{child}");
                    if !nodes.iter().any(|n| n.id == child_node) {
                        nodes.push(GraphNode {
                            id: child_node.clone(),
                            kind: "run".to_string(),
                            label: format!("run {child}"),
                            metadata: Some(json!({ "delegated": true })),
                        });
                    }
                    edges.push(GraphEdge {
                        from: run_node.clone(),
                        to: child_node,
                        edge_type: "delegation".to_string(),
                        metadata: lin.delegation_reason.as_ref().map(|r| json!({ "reason": r })),
                    });
                }
            }
            "tool_call" => {
                delegation_types.insert("tool_execution".to_string());
                let tool_name = ev
                    .payload
                    .get("tool_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("tool");
                let tool_node = format!("tool:{tool_name}");
                if !nodes.iter().any(|n| n.id == tool_node) {
                    nodes.push(GraphNode {
                        id: tool_node.clone(),
                        kind: "tool".to_string(),
                        label: tool_name.to_string(),
                        metadata: None,
                    });
                }
                edges.push(GraphEdge {
                    from: ev_node.clone(),
                    to: tool_node,
                    edge_type: "tool".to_string(),
                    metadata: None,
                });
            }
            _ => {}
        }
    }

    nodes.sort_by(|a, b| a.id.cmp(&b.id).then_with(|| a.kind.cmp(&b.kind)));
    edges.sort_by(|a, b| {
        a.from
            .cmp(&b.from)
            .then_with(|| a.to.cmp(&b.to))
            .then_with(|| a.edge_type.cmp(&b.edge_type))
    });
    let mut delegation_types: Vec<String> = delegation_types.into_iter().collect();
    delegation_types.sort();
    let mut governance_gates: Vec<String> = governance_gates.into_iter().collect();
    governance_gates.sort();

    (nodes, edges, delegation_types, governance_gates)
}

fn add_gate_node(nodes: &mut Vec<GraphNode>, edges: &mut Vec<GraphEdge>, id: &str, label: &str, ev_node: &str) {
    if !nodes.iter().any(|n| n.id == id) {
        nodes.push(GraphNode {
            id: id.to_string(),
            kind: "gate".to_string(),
            label: label.to_string(),
            metadata: None,
        });
    }
    edges.push(GraphEdge {
        from: ev_node.to_string(),
        to: id.to_string(),
        edge_type: "governance_gate".to_string(),
        metadata: None,
    });
}

pub fn graph_to_mermaid(doc: &GovernanceGraphDocument) -> String {
    let g = &doc.graph;
    let mut lines = vec!["flowchart TD".to_string()];
    for n in &g.nodes {
        let shape = match n.kind.as_str() {
            "run" => format!("{}[[\"{}\"]]", mermaid_id(&n.id), escape_mermaid(&n.label)),
            "gate" => format!("{}{{\"{}\"}}", mermaid_id(&n.id), escape_mermaid(&n.label)),
            _ => format!("{}[\"{}\"]", mermaid_id(&n.id), escape_mermaid(&n.label)),
        };
        lines.push(shape);
    }
    for e in &g.edges {
        let arrow = match e.edge_type.as_str() {
            "delegation" => "-- delegate -->",
            "sequence" => "-->>",
            "governance_gate" => "-. gate .->",
            "tool" => "-- tool -->",
            _ => "-->",
        };
        lines.push(format!(
            "{} {} {}",
            mermaid_id(&e.from),
            arrow,
            mermaid_id(&e.to)
        ));
    }
    lines.join("\n")
}

fn mermaid_id(id: &str) -> String {
    id.replace(':', "_").replace('-', "_")
}

fn escape_mermaid(s: &str) -> String {
    s.replace('"', "'")
}

pub fn governance_graph_from_export(export: &Value) -> Result<GovernanceGraphDocument, String> {
    let run_id = export
        .get("run")
        .and_then(|r| r.get("run_id"))
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .ok_or_else(|| "export.run.run_id is required".to_string())?;
    let arr = export
        .get("evidence_events")
        .and_then(|v| v.as_array())
        .ok_or_else(|| "evidence_events must be an array".to_string())?;
    let mut events = Vec::with_capacity(arr.len());
    for item in arr {
        let ev: EvidenceEvent =
            serde_json::from_value(item.clone()).map_err(|e| format!("invalid evidence event: {e}"))?;
        events.push(ev);
    }
    Ok(build_governance_graph(&run_id, &events))
}

pub fn lineage_block_from_graph(doc: &GovernanceGraphDocument) -> Value {
    json!({
        "root_run_id": doc.graph.root_run_id,
        "parent_run_id": doc.lineage_records.iter()
            .find(|r| r.run_id == doc.graph.run_id)
            .and_then(|r| r.lineage.parent_run_id.clone()),
        "lineage_integrity_status": doc.graph.lineage_integrity_status,
        "delegation_types": doc.graph.delegation_types,
        "governance_gates": doc.graph.governance_gates,
        "graph": {
            "schema_version": doc.schema_version,
            "nodes": doc.graph.nodes,
            "edges": doc.graph.edges,
        },
        "validation": doc.graph.lineage_validation,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn mermaid_output_stable() {
        let ev = EvidenceEvent {
            event_id: "e1".into(),
            event_type: "ai_discovery_reported".into(),
            ts_utc: "2026-01-01T00:00:00Z".into(),
            actor: "a".into(),
            system: "s".into(),
            run_id: "run-root".into(),
            environment: None,
            payload: json!({}),
            parent_run_id: None,
            root_run_id: Some("run-root".into()),
            delegated_from_event_id: None,
            agent_id: Some("planner".into()),
            agent_role: Some("orchestrator".into()),
            delegation_reason: None,
        };
        let doc = build_governance_graph("run-root", &[ev]);
        let m1 = graph_to_mermaid(&doc);
        let m2 = graph_to_mermaid(&doc);
        assert_eq!(m1, m2);
        assert!(m1.contains("flowchart TD"));
    }
}
