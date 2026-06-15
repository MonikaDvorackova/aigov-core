//! Recursive key-sorted JSON canonicalization shared by signing and bundle digests.

use serde::Serialize;
use serde_json::Value;
use sha2::{Digest, Sha256};

pub fn sort_json_value(v: Value) -> Value {
    match v {
        Value::Object(map) => {
            let mut items: Vec<(String, Value)> = map.into_iter().collect();
            items.sort_by(|a, b| a.0.cmp(&b.0));
            let mut out = serde_json::Map::new();
            for (k, vv) in items {
                out.insert(k, sort_json_value(vv));
            }
            Value::Object(out)
        }
        Value::Array(arr) => Value::Array(arr.into_iter().map(sort_json_value).collect()),
        other => other,
    }
}

pub fn canonical_json_bytes<T: Serialize>(value: &T) -> Vec<u8> {
    let v = serde_json::to_value(value).expect("to_value");
    let sorted = sort_json_value(v);
    serde_json::to_vec(&sorted).expect("to_vec")
}

pub fn sha256_hex_bytes(bytes: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(bytes);
    hex::encode(h.finalize())
}

pub fn sha256_hex_json<T: Serialize>(value: &T) -> String {
    sha256_hex_bytes(&canonical_json_bytes(value))
}
