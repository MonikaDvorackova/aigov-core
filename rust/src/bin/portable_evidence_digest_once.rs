//! Offline helper: print `bundle::portable_evidence_digest_v1` for a bundle JSON file.
//! Usage: `portable_evidence_digest_once <run_id> <path-to-bundle.json>`
//! The bundle must be a JSON object with an `events` array of evidence events.

use aigov_audit::bundle::portable_evidence_digest_v1;
use aigov_audit::schema::EvidenceEvent;

fn main() {
    let mut args = std::env::args().skip(1);
    let run_id = args.next().expect("run_id required");
    let path = args.next().expect("bundle.json path required");
    let txt = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read {path}: {e}"));
    let bundle: serde_json::Value =
        serde_json::from_str(&txt).unwrap_or_else(|e| panic!("parse bundle: {e}"));
    let arr = bundle
        .get("events")
        .and_then(|v| v.as_array())
        .expect("bundle.events must be an array");
    let mut events: Vec<EvidenceEvent> = Vec::with_capacity(arr.len());
    for (i, e) in arr.iter().enumerate() {
        let ev: EvidenceEvent = serde_json::from_value(e.clone())
            .unwrap_or_else(|e| panic!("events[{i}] not EvidenceEvent: {e}"));
        events.push(ev);
    }
    println!("{}", portable_evidence_digest_v1(&run_id, &events));
}
