use crate::schema::EvidenceEvent;
use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
#[cfg(test)]
use std::cell::Cell;
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::Instant;

/// Integration / manual tests only: when `AIGOV_TEST_APPEND_FAIL=1`, [`append_record`] errors before I/O.
fn append_fail_test_hook_active() -> bool {
    matches!(
        std::env::var("AIGOV_TEST_APPEND_FAIL").as_deref(),
        Ok("1") | Ok("true")
    )
}

const GENESIS: &str = "GENESIS";
const STATE_SUFFIX: &str = ".state.json";
const CHECKPOINTS_SUFFIX: &str = ".checkpoints.jsonl";

#[cfg(test)]
thread_local! {
    static LEDGER_STATE_SCAN_CALLS: Cell<usize> = Cell::new(0);
}

#[cfg(test)]
thread_local! {
    static RUN_INDEX_REBUILD_CALLS: Cell<usize> = Cell::new(0);
}

static LEDGER_LOCKS: Lazy<Mutex<HashMap<String, Arc<Mutex<()>>>>> =
    Lazy::new(|| Mutex::new(HashMap::new()));

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoredRecord {
    pub prev_hash: String,
    pub record_hash: String,
    pub event_json: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LedgerCheckpoint {
    pub run_id: String,
    pub last_event_id: String,
    /// Digest of ledger event content in file order up to (and including) `last_event_id`.
    pub events_content_sha256: String,
    /// Timestamp (UTC) associated with the checkpoint (derived from the referenced last event).
    pub ts_utc: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct LedgerState {
    last_hash: String,
    record_count: u64,
    last_valid_offset: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TrailingCorruption {
    pub line_no: usize,
    pub byte_offset_start: u64,
    pub byte_offset_end: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LedgerScanDiagnostics {
    pub trailing_corruption: Option<TrailingCorruption>,
}

#[derive(Debug, Clone)]
struct LedgerScan {
    records: Vec<StoredRecord>,
    diagnostics: LedgerScanDiagnostics,
    /// Byte offset immediately after the last valid (or ignorable blank) line.
    last_valid_byte_end: u64,
}

fn sha256_hex(input: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(input);
    let out = hasher.finalize();
    hex::encode(out)
}

fn compute_record_hash(prev_hash: &str, event_json: &str) -> String {
    let mut bytes = Vec::with_capacity(prev_hash.len() + 1 + event_json.len());
    bytes.extend_from_slice(prev_hash.as_bytes());
    bytes.push(b'\n');
    bytes.extend_from_slice(event_json.as_bytes());
    sha256_hex(&bytes)
}

fn canonical_ledger_key(log_path: &str) -> Result<String, String> {
    let p = Path::new(log_path);
    if let Ok(canon) = std::fs::canonicalize(p) {
        return Ok(canon.to_string_lossy().to_string());
    }

    let parent = p.parent().unwrap_or_else(|| Path::new("."));
    let parent_canon = std::fs::canonicalize(parent).map_err(|e| e.to_string())?;
    let joined: PathBuf = parent_canon.join(p.file_name().unwrap_or_default());
    Ok(joined.to_string_lossy().to_string())
}

fn lock_for_ledger(log_path: &str) -> Result<Arc<Mutex<()>>, String> {
    let key = canonical_ledger_key(log_path)?;
    let mut map = LEDGER_LOCKS
        .lock()
        .map_err(|_| "ledger lock poisoned".to_string())?;
    Ok(map
        .entry(key)
        .or_insert_with(|| Arc::new(Mutex::new(())))
        .clone())
}

fn ensure_parent_dir_exists(path: &str) -> Result<(), String> {
    let p = Path::new(path);
    let parent = match p.parent() {
        Some(pp) if !pp.as_os_str().is_empty() && pp != Path::new(".") => pp,
        _ => return Ok(()),
    };
    std::fs::create_dir_all(parent).map_err(|e| {
        format!(
            "Failed to create ledger parent directory {}: {e}",
            parent.display()
        )
    })?;
    Ok(())
}

fn state_path_for_ledger(log_path: &str) -> String {
    format!("{log_path}{STATE_SUFFIX}")
}

fn checkpoints_path_for_ledger(log_path: &str) -> String {
    format!("{log_path}{CHECKPOINTS_SUFFIX}")
}

fn sanitize_segment(s: &str) -> String {
    let out: String = s
        .chars()
        .map(|c| match c {
            'a'..='z' | 'A'..='Z' | '0'..='9' | '-' | '_' => c,
            _ => '_',
        })
        .take(128)
        .collect();
    if out.is_empty() {
        "_".to_string()
    } else {
        out
    }
}

fn run_index_path_for_ledger(log_path: &str, run_id: &str) -> String {
    let safe = sanitize_segment(run_id);
    format!("{log_path}.run.{safe}.events")
}

fn load_state_if_valid(log_path: &str) -> Option<LedgerState> {
    let p = state_path_for_ledger(log_path);
    let raw = std::fs::read_to_string(p).ok()?;
    let s: LedgerState = serde_json::from_str(&raw).ok()?;
    if s.last_hash.trim().is_empty() {
        return None;
    }
    Some(s)
}

fn sync_parent_dir_best_effort(path: &Path) {
    #[cfg(unix)]
    {
        if let Some(parent) = path.parent() {
            if let Ok(dir) = File::open(parent) {
                let _ = dir.sync_all();
            }
        }
    }
}

fn write_state_atomic(log_path: &str, state: &LedgerState) -> Result<(), String> {
    let state_path = PathBuf::from(state_path_for_ledger(log_path));
    let parent = state_path.parent().unwrap_or_else(|| Path::new("."));
    std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;

    let pid = std::process::id();
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let tmp_path = state_path.with_extension(format!(
        "{}tmp.{}.{}",
        state_path
            .extension()
            .and_then(|s| s.to_str())
            .unwrap_or(""),
        pid,
        nanos
    ));

    let bytes = serde_json::to_vec(state).map_err(|e| e.to_string())?;
    let mut f = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&tmp_path)
        .map_err(|e| e.to_string())?;
    f.write_all(&bytes).map_err(|e| e.to_string())?;
    f.write_all(b"\n").map_err(|e| e.to_string())?;
    f.flush().map_err(|e| e.to_string())?;

    let skip_fsync = std::env::var("GOVAI_SKIP_FSYNC")
        .ok()
        .map(|v| v == "1" || v.eq_ignore_ascii_case("true"))
        .unwrap_or(false);

    if !skip_fsync {
        f.sync_data().map_err(|e| e.to_string())?;
    }
    drop(f);

    std::fs::rename(&tmp_path, &state_path).map_err(|e| e.to_string())?;
    sync_parent_dir_best_effort(&state_path);

    if let Ok(sf) = File::open(&state_path) {
        let _ = sf.sync_data();
    }
    Ok(())
}

fn scan_ledger_state_tolerant(
    log_path: &str,
) -> Result<(LedgerState, LedgerScanDiagnostics), String> {
    #[cfg(test)]
    {
        LEDGER_STATE_SCAN_CALLS.with(|c| c.set(c.get() + 1));
    }
    let f = match File::open(log_path) {
        Ok(f) => f,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            return Ok((
                LedgerState {
                    last_hash: GENESIS.to_string(),
                    record_count: 0,
                    last_valid_offset: 0,
                },
                LedgerScanDiagnostics {
                    trailing_corruption: None,
                },
            ));
        }
        Err(e) => return Err(e.to_string()),
    };

    let mut reader = BufReader::new(f);
    let mut buf: Vec<u8> = Vec::new();
    let mut offset: u64 = 0;
    let mut line_no: usize = 0;
    let mut last_hash: String = GENESIS.to_string();
    let mut record_count: u64 = 0;
    let mut last_valid_offset: u64 = 0;
    let mut trailing: Option<TrailingCorruption> = None;

    loop {
        buf.clear();
        let start_offset = offset;
        let n = reader
            .read_until(b'\n', &mut buf)
            .map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        offset = offset
            .checked_add(n as u64)
            .ok_or_else(|| "ledger scan offset overflow".to_string())?;

        let line = std::str::from_utf8(&buf).map_err(|e| {
            format!(
                "ledger contains non-utf8 bytes at offset {}: {}",
                start_offset, e
            )
        })?;
        let t = line.trim();
        if t.is_empty() {
            last_valid_offset = offset;
            continue;
        }

        line_no += 1;
        match serde_json::from_str::<StoredRecord>(t) {
            Ok(rec) => {
                last_hash = rec.record_hash;
                record_count = record_count
                    .checked_add(1)
                    .ok_or_else(|| "ledger record_count overflow".to_string())?;
                last_valid_offset = offset;
            }
            Err(e) => {
                let at_eof = reader.fill_buf().map_err(|e| e.to_string())?.is_empty();
                if at_eof {
                    trailing = Some(TrailingCorruption {
                        line_no,
                        byte_offset_start: start_offset,
                        byte_offset_end: offset,
                    });
                    break;
                }
                return Err(format!(
                    "ledger corruption before EOF at line {} (offset {}): {}",
                    line_no, start_offset, e
                ));
            }
        }
    }

    Ok((
        LedgerState {
            last_hash,
            record_count,
            last_valid_offset,
        },
        LedgerScanDiagnostics {
            trailing_corruption: trailing,
        },
    ))
}

fn repair_trailing_partial_record_fast(log_path: &str) -> Result<bool, String> {
    let mut f = match OpenOptions::new().read(true).write(true).open(log_path) {
        Ok(f) => f,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(false),
        Err(e) => return Err(e.to_string()),
    };
    let len = f.metadata().map_err(|e| e.to_string())?.len();
    if len == 0 {
        return Ok(false);
    }

    f.seek(SeekFrom::End(-1)).map_err(|e| e.to_string())?;
    let mut last = [0u8; 1];
    f.read_exact(&mut last).map_err(|e| e.to_string())?;
    if last[0] == b'\n' {
        return Ok(false);
    }

    let win: u64 = 64 * 1024;
    let start = if len > win { len - win } else { 0 };
    f.seek(SeekFrom::Start(start)).map_err(|e| e.to_string())?;
    let mut buf = vec![0u8; (len - start) as usize];
    f.read_exact(&mut buf).map_err(|e| e.to_string())?;

    let mut cut = None;
    for (i, b) in buf.iter().enumerate().rev() {
        if *b == b'\n' {
            cut = Some(start + i as u64 + 1);
            break;
        }
    }
    let new_len = cut.unwrap_or(0);
    if new_len == len {
        return Ok(false);
    }
    f.set_len(new_len).map_err(|e| e.to_string())?;
    f.seek(SeekFrom::End(0)).map_err(|e| e.to_string())?;
    f.flush().map_err(|e| e.to_string())?;
    f.sync_data().map_err(|e| e.to_string())?;
    Ok(true)
}

fn load_or_rebuild_state(log_path: &str, force_rebuild: bool) -> Result<LedgerState, String> {
    if !force_rebuild {
        if let Some(s) = load_state_if_valid(log_path) {
            return Ok(s);
        }
    }

    let (state, diag) = scan_ledger_state_tolerant(log_path)?;
    if diag.trailing_corruption.is_some() {
        return Err(
            "ledger has trailing corruption; repair required before rebuilding state".to_string(),
        );
    }
    write_state_atomic(log_path, &state)?;
    Ok(state)
}

fn load_or_rebuild_run_index(log_path: &str, run_id: &str) -> Result<HashSet<String>, String> {
    let p = run_index_path_for_ledger(log_path, run_id);
    if let Ok(raw) = std::fs::read_to_string(&p) {
        let mut out: HashSet<String> = HashSet::new();
        for line in raw.lines() {
            let t = line.trim();
            if t.is_empty() {
                continue;
            }
            out.insert(t.to_string());
        }
        return Ok(out);
    }

    // Rebuild once by scanning the ledger stream for this run only.
    #[cfg(test)]
    {
        RUN_INDEX_REBUILD_CALLS.with(|c| c.set(c.get() + 1));
    }
    let f = match File::open(log_path) {
        Ok(f) => f,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            std::fs::write(&p, "").map_err(|e| e.to_string())?;
            return Ok(HashSet::new());
        }
        Err(e) => return Err(e.to_string()),
    };
    let mut reader = BufReader::new(f);
    let mut buf: Vec<u8> = Vec::new();
    let mut out: HashSet<String> = HashSet::new();
    let mut offset: u64 = 0;
    let mut line_no: usize = 0;
    loop {
        buf.clear();
        let start_offset = offset;
        let n = reader
            .read_until(b'\n', &mut buf)
            .map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        offset = offset
            .checked_add(n as u64)
            .ok_or_else(|| "ledger scan offset overflow".to_string())?;
        let line = std::str::from_utf8(&buf).map_err(|e| {
            format!(
                "ledger contains non-utf8 bytes at offset {}: {}",
                start_offset, e
            )
        })?;
        let t = line.trim();
        if t.is_empty() {
            continue;
        }
        line_no += 1;
        match serde_json::from_str::<StoredRecord>(t) {
            Ok(rec) => {
                let ev: EvidenceEvent =
                    serde_json::from_str(&rec.event_json).map_err(|e| e.to_string())?;
                if ev.run_id == run_id {
                    out.insert(ev.event_id);
                }
            }
            Err(e) => {
                let at_eof = reader.fill_buf().map_err(|e| e.to_string())?.is_empty();
                if at_eof {
                    break;
                }
                return Err(format!(
                    "ledger corruption before EOF at line {} (offset {}): {}",
                    line_no, start_offset, e
                ));
            }
        }
    }

    let mut lines: Vec<String> = out.iter().cloned().collect();
    lines.sort();
    std::fs::write(&p, format!("{}\n", lines.join("\n"))).map_err(|e| e.to_string())?;
    Ok(out)
}

fn append_event_id_to_run_index(
    log_path: &str,
    run_id: &str,
    event_id: &str,
) -> Result<(), String> {
    let p = run_index_path_for_ledger(log_path, run_id);
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&p)
        .map_err(|e| e.to_string())?;
    f.write_all(event_id.as_bytes())
        .map_err(|e| e.to_string())?;
    f.write_all(b"\n").map_err(|e| e.to_string())?;
    f.flush().map_err(|e| e.to_string())?;
    f.sync_data().map_err(|e| e.to_string())?;
    Ok(())
}

pub fn append_record(log_path: &str, event: EvidenceEvent) -> Result<StoredRecord, String> {
    Ok(append_record_atomic_with_run_count(log_path, event)?.0)
}

/// Atomically append a record to the ledger with single-writer semantics per ledger path.
/// Returns `(stored_record, pre_count_for_run_id)` on success.
pub fn append_record_atomic_with_run_count(
    log_path: &str,
    event: EvidenceEvent,
) -> Result<(StoredRecord, usize), String> {
    if append_fail_test_hook_active() {
        return Err("test_simulated_append_failure".to_string());
    }

    // Ensure the ledger directory exists *before* we canonicalize for locking or open the file.
    // This avoids surprising "No such file or directory" failures when GOVAI_LEDGER_DIR points to
    // a not-yet-created path (common in CI/container environments).
    ensure_parent_dir_exists(log_path)?;

    // Temporary structured diagnostics (Railway 15s timeout investigation).
    // Do not log secrets; run_id/event_id are identifiers, not credentials.
    let t0 = Instant::now();
    eprintln!(
        "audit_append phase=begin log_path={} run_id={} event_id={}",
        log_path, event.run_id, event.event_id
    );
    eprintln!(
        "audit_append phase=before_lock log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );

    let lock = lock_for_ledger(log_path)?;
    let _guard = lock
        .lock()
        .map_err(|_| "ledger lock poisoned".to_string())?;
    eprintln!(
        "audit_append phase=after_lock log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );

    // Critical section (single-writer per ledger):
    // - reject duplicate event_id using per-run sidecar index (no full-ledger scan on hot path)
    // - repair trailing partial line (fast tail check) before state/index use
    // - load state file (rebuild once by scanning if missing/invalid, or after repair)
    // - append record with flush + sync_data
    // - update state atomically (temp + rename + sync)
    // - update run index after successful append

    eprintln!(
        "audit_append phase=before_run_index log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );
    let seen = load_or_rebuild_run_index(log_path, &event.run_id)?;
    if seen.contains(&event.event_id) {
        return Err(format!(
            "duplicate event_id for run_id: event_id={} run_id={}",
            event.event_id, event.run_id
        ));
    }
    let pre_count: usize = seen.len();

    eprintln!(
        "audit_append phase=before_repair log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );
    let repaired_tail = repair_trailing_partial_record_fast(log_path)?;
    eprintln!(
        "audit_append phase=after_repair log_path={} repaired_tail={} elapsed_ms={}",
        log_path,
        repaired_tail,
        t0.elapsed().as_millis()
    );

    eprintln!(
        "audit_append phase=before_state log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );
    let state = load_or_rebuild_state(log_path, repaired_tail)?;
    eprintln!(
        "audit_append phase=after_state log_path={} record_count={} elapsed_ms={}",
        log_path,
        state.record_count,
        t0.elapsed().as_millis()
    );

    let prev_hash = state.last_hash.clone();
    let event_json = serde_json::to_string(&event).map_err(|e| e.to_string())?;
    let record_hash = compute_record_hash(&prev_hash, &event_json);

    let rec = StoredRecord {
        prev_hash,
        record_hash,
        event_json,
    };

    eprintln!(
        "audit_append phase=before_write log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_path)
        .map_err(|e| e.to_string())?;

    let line = serde_json::to_string(&rec).map_err(|e| e.to_string())?;
    f.write_all(line.as_bytes()).map_err(|e| e.to_string())?;
    f.write_all(b"\n").map_err(|e| e.to_string())?;
    eprintln!(
        "audit_append phase=after_write log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );

    eprintln!(
        "audit_append phase=before_flush log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );
    f.flush().map_err(|e| e.to_string())?;
    eprintln!(
        "audit_append phase=after_flush log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );
    // Best-effort durable semantics: sync file data and metadata as supported.
    // If sync fails, surface the error (do not silently continue).
    eprintln!(
        "audit_append phase=before_sync_data log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );
    f.sync_data().map_err(|e| e.to_string())?;
    eprintln!(
        "audit_append phase=after_sync_data log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );

    let new_offset = f.metadata().map_err(|e| e.to_string())?.len();

    // Update state atomically (required for hot path performance).
    eprintln!(
        "audit_append phase=before_state_write log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );
    let new_state = LedgerState {
        last_hash: rec.record_hash.clone(),
        record_count: state.record_count + 1,
        last_valid_offset: new_offset,
    };
    write_state_atomic(log_path, &new_state)?;
    eprintln!(
        "audit_append phase=after_state_write log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );

    // Update run index (cache). Do this after durable append; do not fail the request if it fails.
    if let Err(e) = append_event_id_to_run_index(log_path, &event.run_id, &event.event_id) {
        eprintln!(
            "audit_append phase=run_index_update_failed log_path={} run_id={} event_id={} err={}",
            log_path, event.run_id, event.event_id, e
        );
    }

    eprintln!(
        "audit_append phase=done log_path={} elapsed_ms={}",
        log_path,
        t0.elapsed().as_millis()
    );
    Ok((rec, pre_count))
}

fn scan_checkpoints_tolerant(log_path: &str) -> Result<Vec<LedgerCheckpoint>, String> {
    let p = checkpoints_path_for_ledger(log_path);
    let f = match File::open(&p) {
        Ok(f) => f,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(e) => return Err(e.to_string()),
    };
    let mut reader = BufReader::new(f);
    let mut buf: Vec<u8> = Vec::new();
    let mut out: Vec<LedgerCheckpoint> = Vec::new();
    let mut offset: u64 = 0;
    let mut line_no: usize = 0;
    loop {
        buf.clear();
        let n = reader
            .read_until(b'\n', &mut buf)
            .map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        offset = offset
            .checked_add(n as u64)
            .ok_or_else(|| "checkpoint scan offset overflow".to_string())?;
        let line = std::str::from_utf8(&buf).map_err(|e| {
            format!(
                "checkpoint file contains non-utf8 bytes at offset {}: {}",
                offset.saturating_sub(n as u64),
                e
            )
        })?;
        let t = line.trim();
        if t.is_empty() {
            continue;
        }
        line_no += 1;
        match serde_json::from_str::<LedgerCheckpoint>(t) {
            Ok(cp) => out.push(cp),
            Err(e) => {
                let at_eof = reader.fill_buf().map_err(|e| e.to_string())?.is_empty();
                if at_eof {
                    break;
                }
                return Err(format!(
                    "checkpoint corruption before EOF at line {}: {}",
                    line_no, e
                ));
            }
        }
    }
    Ok(out)
}

pub fn latest_checkpoint(log_path: &str) -> Result<Option<LedgerCheckpoint>, String> {
    let cps = scan_checkpoints_tolerant(log_path)?;
    Ok(cps.into_iter().last())
}

/// Compute a deterministic digest over *ledger event content* in file order.
///
/// This does **not** use the hash chain; it is an independent integrity anchor derived from stored event JSON.
pub fn compute_ledger_events_content_sha256(
    log_path: &str,
) -> Result<(String, Option<(EvidenceEvent, String)>), String> {
    let scan = scan_ledger_records_tolerant(log_path)?;
    let mut h = Sha256::new();
    let mut last_ev: Option<EvidenceEvent> = None;
    let mut last_digest_hex: Option<String> = None;
    for rec in scan.records {
        // Hash the stored JSON exactly as persisted (no re-serialization).
        h.update(rec.event_json.as_bytes());
        h.update(b"\n");
        let ev: EvidenceEvent = serde_json::from_str(&rec.event_json).map_err(|e| e.to_string())?;
        last_ev = Some(ev);
        // Snapshot digest after this event for checkpoint mapping.
        last_digest_hex = Some(hex::encode(h.clone().finalize()));
    }
    let digest_hex = hex::encode(h.finalize());
    Ok((
        digest_hex,
        match (last_ev, last_digest_hex) {
            (Some(ev), Some(d)) => Some((ev, d)),
            _ => None,
        },
    ))
}

/// Append a checkpoint record (append-only, fsync).
pub fn append_checkpoint(log_path: &str, cp: &LedgerCheckpoint) -> Result<(), String> {
    ensure_parent_dir_exists(log_path)?;
    let p = checkpoints_path_for_ledger(log_path);
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&p)
        .map_err(|e| e.to_string())?;
    let line = serde_json::to_string(cp).map_err(|e| e.to_string())?;
    f.write_all(line.as_bytes()).map_err(|e| e.to_string())?;
    f.write_all(b"\n").map_err(|e| e.to_string())?;
    f.flush().map_err(|e| e.to_string())?;
    f.sync_data().map_err(|e| e.to_string())?;
    Ok(())
}

/// Ensure a fresh checkpoint exists for the current ledger head.
///
/// This is an explicit trigger used by export/ops paths; it never mutates the main ledger.
pub fn ensure_checkpoint_current(log_path: &str) -> Result<Option<LedgerCheckpoint>, String> {
    let (digest, last) = compute_ledger_events_content_sha256(log_path)?;
    let Some((ev, digest_at_last)) = last else {
        return Ok(None);
    };
    // digest_at_last should equal digest when ev is the final record.
    let digest_at_last = if digest_at_last.is_empty() {
        digest.clone()
    } else {
        digest_at_last
    };
    let existing = latest_checkpoint(log_path)?;
    if let Some(ref cp) = existing {
        if cp.run_id == ev.run_id
            && cp.last_event_id == ev.event_id
            && cp.events_content_sha256 == digest_at_last
        {
            return Ok(existing);
        }
    }
    let cp = LedgerCheckpoint {
        run_id: ev.run_id.clone(),
        last_event_id: ev.event_id.clone(),
        events_content_sha256: digest_at_last,
        ts_utc: ev.ts_utc.clone(),
    };
    append_checkpoint(log_path, &cp)?;
    Ok(Some(cp))
}

/// Verify checkpoint continuity: each checkpoint must match the digest computed from the ledger up to its last event.
pub fn verify_checkpoints(log_path: &str) -> Result<(), String> {
    let cps = scan_checkpoints_tolerant(log_path)?;
    if cps.is_empty() {
        return Ok(());
    }

    // Precompute digest snapshots for each (run_id, event_id) pair in ledger order.
    let scan = scan_ledger_records_tolerant(log_path)?;
    let mut h = Sha256::new();
    let mut snapshots: HashMap<(String, String), String> = HashMap::new();
    for rec in scan.records {
        h.update(rec.event_json.as_bytes());
        h.update(b"\n");
        let ev: EvidenceEvent = serde_json::from_str(&rec.event_json).map_err(|e| e.to_string())?;
        let d = hex::encode(h.clone().finalize());
        snapshots.insert((ev.run_id, ev.event_id), d);
    }

    for (i, cp) in cps.iter().enumerate() {
        let key = (cp.run_id.clone(), cp.last_event_id.clone());
        let Some(expected) = snapshots.get(&key) else {
            return Err(format!(
                "checkpoint_invalid index={} reason=missing_last_event run_id={} last_event_id={}",
                i, cp.run_id, cp.last_event_id
            ));
        };
        if expected != &cp.events_content_sha256 {
            return Err(format!(
                "checkpoint_invalid index={} reason=digest_mismatch run_id={} last_event_id={} expected={} actual={}",
                i, cp.run_id, cp.last_event_id, expected, cp.events_content_sha256
            ));
        }
    }
    Ok(())
}

/// Scan a JSONL ledger file and tolerate exactly one trailing partial/corrupted line.
///
/// Behavior:
/// - Valid JSON lines parse into [`StoredRecord`].
/// - Blank/whitespace-only lines are ignored.
/// - If a JSON parse error occurs on the final line (EOF), it is treated as a
///   *recoverable trailing corruption*: it is ignored for scans but reported in diagnostics.
/// - If a JSON parse error occurs before the final line, it is treated as *hard corruption*
///   and scanning fails.
fn scan_ledger_records_tolerant(log_path: &str) -> Result<LedgerScan, String> {
    let f = match File::open(log_path) {
        Ok(f) => f,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            return Ok(LedgerScan {
                records: Vec::new(),
                diagnostics: LedgerScanDiagnostics {
                    trailing_corruption: None,
                },
                last_valid_byte_end: 0,
            });
        }
        Err(e) => return Err(e.to_string()),
    };

    let mut reader = BufReader::new(f);
    let mut buf: Vec<u8> = Vec::new();
    let mut records: Vec<StoredRecord> = Vec::new();
    let mut offset: u64 = 0;
    let mut last_valid_byte_end: u64 = 0;
    let mut line_no: usize = 0;
    let mut trailing: Option<TrailingCorruption> = None;

    loop {
        buf.clear();
        let start_offset = offset;
        let n = reader
            .read_until(b'\n', &mut buf)
            .map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        offset = offset
            .checked_add(n as u64)
            .ok_or_else(|| "ledger scan offset overflow".to_string())?;

        // Remove UTF-8 BOM or ensure UTF-8? Ledger is expected to be UTF-8 JSON.
        let line = std::str::from_utf8(&buf).map_err(|e| {
            format!(
                "ledger contains non-utf8 bytes at offset {}: {}",
                start_offset, e
            )
        })?;
        let t = line.trim();
        if t.is_empty() {
            // Blank lines are ignorable but still "valid" from a truncation safety perspective.
            last_valid_byte_end = offset;
            continue;
        }

        line_no += 1;
        match serde_json::from_str::<StoredRecord>(t) {
            Ok(rec) => {
                records.push(rec);
                last_valid_byte_end = offset;
            }
            Err(e) => {
                // Determine whether this is the final line (EOF).
                let at_eof = reader.fill_buf().map_err(|e| e.to_string())?.is_empty();
                if at_eof {
                    trailing = Some(TrailingCorruption {
                        line_no,
                        byte_offset_start: start_offset,
                        byte_offset_end: offset,
                    });
                    // Do not update last_valid_byte_end; do not push a record.
                    // Ignore for scan results.
                    break;
                }
                return Err(format!(
                    "ledger corruption before EOF at line {} (offset {}): {}",
                    line_no, start_offset, e
                ));
            }
        }
    }

    Ok(LedgerScan {
        records,
        diagnostics: LedgerScanDiagnostics {
            trailing_corruption: trailing,
        },
        last_valid_byte_end,
    })
}

/// Public/shared ledger scan entrypoint.
///
/// Returns `(records, diagnostics)`. If `diagnostics.trailing_corruption` is present,
/// the returned `records` contain only the valid committed records before the corrupted tail.
pub fn scan_ledger_records(
    log_path: &str,
) -> Result<(Vec<StoredRecord>, LedgerScanDiagnostics), String> {
    let scan = scan_ledger_records_tolerant(log_path)?;
    Ok((scan.records, scan.diagnostics))
}

/// Repair a JSONL ledger that contains exactly one trailing partial/corrupted line.
///
/// Returns:
/// - `Ok(true)` if a trailing partial record was detected and truncated.
/// - `Ok(false)` if the ledger is already clean (or missing).
/// - `Err(_)` if non-tail corruption exists.
///
/// IMPORTANT: callers must hold the per-ledger lock (see [`lock_for_ledger`]) so truncation
/// cannot race with concurrent appends.
pub fn repair_trailing_partial_record(log_path: &str) -> Result<bool, String> {
    // If the file doesn't exist, nothing to repair.
    let mut f = match OpenOptions::new().read(true).write(true).open(log_path) {
        Ok(f) => f,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(false),
        Err(e) => return Err(e.to_string()),
    };

    let scan = scan_ledger_records_tolerant(log_path)?;

    let trailing = match scan.diagnostics.trailing_corruption {
        Some(t) => t,
        None => return Ok(false),
    };

    // Sanity: never truncate valid bytes, only remove the trailing invalid tail.
    // `last_valid_byte_end` points to the last known-good boundary.
    let new_len = scan.last_valid_byte_end;
    if new_len > trailing.byte_offset_start {
        // This can happen if the last valid line had trailing whitespace and was considered valid.
        // Truncate to the recorded last-valid byte end regardless.
    }

    f.set_len(new_len).map_err(|e| e.to_string())?;
    // Ensure the file cursor doesn't point past EOF for any subsequent operations.
    f.seek(SeekFrom::End(0)).map_err(|e| e.to_string())?;
    f.flush().map_err(|e| e.to_string())?;
    f.sync_data().map_err(|e| e.to_string())?;

    Ok(true)
}

pub fn verify_chain(log_path: &str) -> Result<(), String> {
    let mut expected_prev = GENESIS.to_string();
    let mut line_no: usize = 0;
    let scan = scan_ledger_records_tolerant(log_path)?;

    for rec in scan.records {
        line_no += 1;

        if rec.prev_hash != expected_prev {
            return Err(format!(
                "hash_chain_broken at line {}: prev_hash mismatch expected={} actual={}",
                line_no, expected_prev, rec.prev_hash
            ));
        }

        let expected_hash = compute_record_hash(&rec.prev_hash, &rec.event_json);
        if rec.record_hash != expected_hash {
            return Err(format!(
                "hash_chain_broken at line {}: record_hash mismatch expected={} actual={}",
                line_no, expected_hash, rec.record_hash
            ));
        }

        expected_prev = rec.record_hash.clone();
    }

    Ok(())
}

/// All append-only log records for a `run_id`, in file order (chain order).
pub fn collect_stored_records_for_run(
    log_path: &str,
    run_id: &str,
) -> Result<Vec<StoredRecord>, String> {
    // Preserve prior behavior: missing file is an error for this call.
    let _ = File::open(log_path).map_err(|e| {
        if e.kind() == std::io::ErrorKind::NotFound {
            format!("log not found: {}", log_path)
        } else {
            e.to_string()
        }
    })?;

    let scan = scan_ledger_records_tolerant(log_path)?;

    let mut out: Vec<StoredRecord> = Vec::new();
    for rec in scan.records {
        let ev: EvidenceEvent = serde_json::from_str(&rec.event_json).map_err(|e| e.to_string())?;
        if ev.run_id == run_id {
            out.push(rec);
        }
    }

    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::sync::Arc;
    use std::thread;

    fn mk_event(run_id: &str, event_id: &str, ts: &str) -> EvidenceEvent {
        EvidenceEvent {
            event_id: event_id.to_string(),
            event_type: "test".to_string(),
            ts_utc: ts.to_string(),
            actor: "tester".to_string(),
            system: "unit".to_string(),
            run_id: run_id.to_string(),
            environment: None,
            payload: json!({"k":"v"}),
        }
    }

    #[test]
    fn concurrent_distinct_events_preserve_hash_chain() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");
        let log_path = log_path.to_string_lossy().to_string();

        let run_id = "r1";
        let n: usize = 32;
        let p = Arc::new(log_path);
        let mut handles = Vec::with_capacity(n);
        for i in 0..n {
            let p1 = Arc::clone(&p);
            handles.push(thread::spawn(move || {
                let ev = mk_event(
                    run_id,
                    &format!("e{i}"),
                    &format!("2026-01-01T00:00:{i:02}Z"),
                );
                append_record(&p1, ev).expect("append");
            }));
        }
        for h in handles {
            h.join().expect("thread join");
        }

        verify_chain(&p).expect("chain valid");
    }

    #[test]
    fn concurrent_duplicate_event_id_is_rejected_deterministically() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");
        let log_path = log_path.to_string_lossy().to_string();

        let run_id = "rdup";
        let event_id = "same";
        let n: usize = 16;
        let p = Arc::new(log_path);
        let mut handles = Vec::with_capacity(n);

        for i in 0..n {
            let p1 = Arc::clone(&p);
            handles.push(thread::spawn(move || {
                let ev = mk_event(run_id, event_id, &format!("2026-01-01T00:00:{i:02}Z"));
                append_record(&p1, ev)
            }));
        }

        let mut ok = 0usize;
        let mut dup = 0usize;
        for h in handles {
            match h.join().expect("thread join") {
                Ok(_) => ok += 1,
                Err(e) => {
                    if e.contains("duplicate event_id for run_id") {
                        dup += 1;
                    } else {
                        panic!("unexpected error: {e}");
                    }
                }
            }
        }
        assert_eq!(ok, 1, "exactly one append should succeed");
        assert_eq!(
            dup,
            n - 1,
            "all other appends should be rejected as duplicates"
        );

        let stored = collect_stored_records_for_run(&p, run_id).expect("collect records");
        let mut matches = 0usize;
        for rec in stored {
            let ev: EvidenceEvent =
                serde_json::from_str(&rec.event_json).expect("parse event_json");
            if ev.event_id == event_id {
                matches += 1;
            }
        }
        assert_eq!(
            matches, 1,
            "ledger must contain exactly one duplicate event_id"
        );
        verify_chain(&p).expect("chain valid");
    }

    #[test]
    fn append_creates_missing_parent_dir_before_canonicalization_and_open() {
        let dir = tempfile::tempdir().expect("tempdir");
        let nested = dir.path().join("missing_parent").join("ledger.jsonl");
        assert!(
            !nested.parent().unwrap().exists(),
            "precondition: parent dir should not exist"
        );

        let log_path = nested.to_string_lossy().to_string();
        let ev = mk_event("r_parent", "e1", "2026-01-01T00:00:00Z");
        append_record(&log_path, ev).expect("append should create parent dir and succeed");

        assert!(
            nested.parent().unwrap().exists(),
            "append should create missing parent directory"
        );
        assert!(nested.exists(), "append should create ledger file");
        verify_chain(&log_path).expect("chain valid");
    }

    #[test]
    fn trailing_partial_line_is_repaired_and_append_succeeds() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");
        let log_path_s = log_path.to_string_lossy().to_string();

        // Seed a valid record.
        let ev1 = mk_event("r1", "e1", "2026-01-01T00:00:00Z");
        append_record(&log_path_s, ev1).expect("append ev1");

        let before = std::fs::read_to_string(&log_path).expect("read");
        assert!(before.lines().count() >= 1);

        // Simulate a crash mid-append by writing a partial JSON object without newline.
        {
            let mut f = OpenOptions::new()
                .append(true)
                .open(&log_path)
                .expect("open append");
            f.write_all(b"{\"prev_hash\":").expect("write partial");
            f.flush().expect("flush");
        }

        // Append should repair tail and succeed.
        let ev2 = mk_event("r1", "e2", "2026-01-01T00:00:01Z");
        append_record(&log_path_s, ev2).expect("append ev2");

        // Chain should still be valid.
        verify_chain(&log_path_s).expect("chain valid after repair+append");

        // Scan should report no trailing corruption and yield exactly two records.
        let (records, diag) = scan_ledger_records(&log_path_s).expect("scan");
        assert!(
            diag.trailing_corruption.is_none(),
            "expected trailing corruption to be repaired"
        );
        assert_eq!(records.len(), 2, "expected exactly two stored records");

        // File ends with a newline (JSONL invariant after a successful append).
        let after_bytes = std::fs::read(&log_path).expect("read bytes");
        assert!(
            after_bytes.last() == Some(&b'\n'),
            "expected ledger to end with newline after append"
        );
    }

    #[test]
    fn non_tail_corruption_still_fails() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");

        // Two valid records.
        let ev1 = mk_event("r1", "e1", "2026-01-01T00:00:00Z");
        let ev2 = mk_event("r1", "e2", "2026-01-01T00:00:01Z");
        append_record(log_path.to_str().unwrap(), ev1).expect("append ev1");
        append_record(log_path.to_str().unwrap(), ev2).expect("append ev2");

        // Corrupt the middle by injecting a bad line between them.
        let raw = std::fs::read_to_string(&log_path).expect("read");
        let mut lines: Vec<&str> = raw.lines().collect();
        assert!(lines.len() >= 2);
        lines.insert(1, "{not json}");
        let rebuilt = lines.join("\n") + "\n";
        std::fs::write(&log_path, rebuilt).expect("write corrupted");

        let err = verify_chain(log_path.to_str().unwrap()).expect_err("must fail");
        assert!(
            err.contains("ledger corruption before EOF"),
            "unexpected error: {err}"
        );
    }

    #[test]
    fn trailing_partial_line_is_detected_by_scan() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");
        let log_path_s = log_path.to_string_lossy().to_string();

        // Seed a valid record.
        let ev1 = mk_event("r1", "e1", "2026-01-01T00:00:00Z");
        append_record(&log_path_s, ev1).expect("append ev1");

        // Add a partial tail.
        {
            let mut f = OpenOptions::new()
                .append(true)
                .open(&log_path)
                .expect("open append");
            f.write_all(b"{\"garbage\":").expect("write partial");
            f.flush().expect("flush");
        }

        let (_records, diag) = scan_ledger_records(&log_path_s).expect("scan ok");
        assert!(
            diag.trailing_corruption.is_some(),
            "expected trailing corruption diagnostics"
        );
    }

    #[test]
    fn repair_errors_on_non_tail_corruption() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");
        let log_path_s = log_path.to_string_lossy().to_string();

        let ev1 = mk_event("r1", "e1", "2026-01-01T00:00:00Z");
        let ev2 = mk_event("r1", "e2", "2026-01-01T00:00:01Z");
        append_record(&log_path_s, ev1).expect("append ev1");
        append_record(&log_path_s, ev2).expect("append ev2");

        let raw = std::fs::read_to_string(&log_path).expect("read");
        let mut lines: Vec<&str> = raw.lines().collect();
        lines.insert(1, "{not json}");
        let rebuilt = lines.join("\n") + "\n";
        std::fs::write(&log_path, rebuilt).expect("write corrupted");

        let err = repair_trailing_partial_record(&log_path_s).expect_err("must error");
        assert!(
            err.contains("ledger corruption before EOF"),
            "unexpected error: {err}"
        );
    }

    #[test]
    fn duplicate_event_id_still_rejected_after_tail_repair() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");
        let log_path_s = log_path.to_string_lossy().to_string();

        // Seed one valid record.
        let ev_seed = mk_event("rdup2", "seed", "2026-01-01T00:00:00Z");
        append_record(&log_path_s, ev_seed).expect("append seed");

        // Add a partial tail to simulate crash.
        {
            let mut f = OpenOptions::new()
                .append(true)
                .open(&log_path)
                .expect("open append");
            f.write_all(b"{").expect("write partial");
            f.flush().expect("flush");
        }

        // Concurrent duplicate event_id appends.
        let n: usize = 8;
        let p = Arc::new(log_path_s);
        let mut handles = Vec::with_capacity(n);
        for i in 0..n {
            let p1 = Arc::clone(&p);
            handles.push(thread::spawn(move || {
                let ev = mk_event("rdup2", "same", &format!("2026-01-01T00:00:{i:02}Z"));
                append_record(&p1, ev)
            }));
        }

        let mut ok = 0usize;
        let mut dup = 0usize;
        for h in handles {
            match h.join().expect("thread join") {
                Ok(_) => ok += 1,
                Err(e) => {
                    if e.contains("duplicate event_id for run_id") {
                        dup += 1;
                    } else {
                        panic!("unexpected error: {e}");
                    }
                }
            }
        }
        assert_eq!(ok, 1, "exactly one append should succeed");
        assert_eq!(
            dup,
            n - 1,
            "all other appends should be rejected as duplicates"
        );

        verify_chain(&p).expect("chain valid");
    }

    fn read_state(log_path: &str) -> LedgerState {
        let p = state_path_for_ledger(log_path);
        let raw = std::fs::read_to_string(&p).expect("read state");
        serde_json::from_str(&raw).expect("parse state")
    }

    fn count_ledger_lines(log_path: &str) -> usize {
        let raw = std::fs::read_to_string(log_path).expect("read ledger");
        raw.lines().filter(|l| !l.trim().is_empty()).count()
    }

    fn reset_counters() {
        LEDGER_STATE_SCAN_CALLS.with(|c| c.set(0));
        RUN_INDEX_REBUILD_CALLS.with(|c| c.set(0));
    }

    #[test]
    fn append_uses_state_without_full_scan_when_present() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");
        let log_path_s = log_path.to_string_lossy().to_string();

        // First append creates ledger + state + run index.
        append_record(
            &log_path_s,
            mk_event("r_state", "e1", "2026-01-01T00:00:00Z"),
        )
        .expect("append e1");
        let st1 = read_state(&log_path_s);
        assert_eq!(st1.record_count, 1);
        assert_eq!(count_ledger_lines(&log_path_s), 1);

        reset_counters();
        append_record(
            &log_path_s,
            mk_event("r_state", "e2", "2026-01-01T00:00:01Z"),
        )
        .expect("append e2");

        // No rebuild scans should be needed when state and run index exist.
        let state_scans = LEDGER_STATE_SCAN_CALLS.with(|c| c.get());
        let idx_rebuilds = RUN_INDEX_REBUILD_CALLS.with(|c| c.get());
        assert_eq!(state_scans, 0);
        assert_eq!(idx_rebuilds, 0);

        let st2 = read_state(&log_path_s);
        assert_eq!(st2.record_count, 2);
        assert_eq!(count_ledger_lines(&log_path_s), 2);
        verify_chain(&log_path_s).expect("chain valid");
    }

    #[test]
    fn missing_state_rebuilds_by_scanning_once() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");
        let log_path_s = log_path.to_string_lossy().to_string();

        append_record(
            &log_path_s,
            mk_event("r_rebuild", "e1", "2026-01-01T00:00:00Z"),
        )
        .expect("append e1");
        std::fs::remove_file(state_path_for_ledger(&log_path_s)).expect("remove state");

        reset_counters();
        append_record(
            &log_path_s,
            mk_event("r_rebuild", "e2", "2026-01-01T00:00:01Z"),
        )
        .expect("append e2");
        let state_scans = LEDGER_STATE_SCAN_CALLS.with(|c| c.get());
        assert!(state_scans >= 1, "expected at least one state rebuild scan");
        verify_chain(&log_path_s).expect("chain valid");
    }

    #[test]
    fn duplicate_event_id_rejected_via_run_index_without_scanning() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");
        let log_path_s = log_path.to_string_lossy().to_string();

        append_record(
            &log_path_s,
            mk_event("r_dupidx", "same", "2026-01-01T00:00:00Z"),
        )
        .expect("append seed");

        reset_counters();
        let err = append_record(
            &log_path_s,
            mk_event("r_dupidx", "same", "2026-01-01T00:00:01Z"),
        )
        .expect_err("must reject duplicate");
        assert!(err.contains("duplicate event_id for run_id"));
        let state_scans = LEDGER_STATE_SCAN_CALLS.with(|c| c.get());
        let idx_rebuilds = RUN_INDEX_REBUILD_CALLS.with(|c| c.get());
        assert_eq!(state_scans, 0);
        assert_eq!(idx_rebuilds, 0);
        verify_chain(&log_path_s).expect("chain valid");
    }

    #[test]
    fn tail_repair_forces_state_rebuild() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");
        let log_path_s = log_path.to_string_lossy().to_string();

        append_record(
            &log_path_s,
            mk_event("r_tail", "e1", "2026-01-01T00:00:00Z"),
        )
        .expect("append e1");

        // Append partial tail (no newline) to simulate crash.
        {
            let mut f = OpenOptions::new()
                .append(true)
                .open(&log_path)
                .expect("open");
            f.write_all(b"{").expect("write partial");
            f.flush().expect("flush");
        }

        reset_counters();
        append_record(
            &log_path_s,
            mk_event("r_tail", "e2", "2026-01-01T00:00:01Z"),
        )
        .expect("append after repair");

        let state_scans = LEDGER_STATE_SCAN_CALLS.with(|c| c.get());
        assert!(state_scans >= 1, "repair should force state rebuild scan");
        verify_chain(&log_path_s).expect("chain valid after repair");
    }

    #[test]
    fn checkpoint_digest_deterministic_and_tamper_detected() {
        let dir = tempfile::tempdir().expect("tempdir");
        let log_path = dir.path().join("ledger.jsonl");
        let log_path_s = log_path.to_string_lossy().to_string();

        append_record(&log_path_s, mk_event("r1", "e1", "2026-01-01T00:00:00Z"))
            .expect("append e1");
        append_record(&log_path_s, mk_event("r2", "e2", "2026-01-01T00:00:01Z"))
            .expect("append e2");

        let cp1 = ensure_checkpoint_current(&log_path_s)
            .expect("checkpoint")
            .expect("non-empty");
        let cp2 = ensure_checkpoint_current(&log_path_s)
            .expect("checkpoint")
            .expect("non-empty");
        assert_eq!(
            cp1, cp2,
            "checkpoint should be stable when ledger unchanged"
        );
        verify_checkpoints(&log_path_s).expect("checkpoints valid");

        // Tamper with the first record's event_json by modifying the persisted line.
        let raw = std::fs::read_to_string(&log_path).expect("read ledger");
        let mut lines: Vec<String> = raw.lines().map(|s| s.to_string()).collect();
        assert!(!lines.is_empty());
        let mut first: StoredRecord =
            serde_json::from_str(lines[0].trim()).expect("parse first record");
        first.event_json = first
            .event_json
            .replace("\"k\":\"v\"", "\"k\":\"tampered\"");
        lines[0] = serde_json::to_string(&first).expect("re-encode record");
        std::fs::write(&log_path, lines.join("\n") + "\n").expect("write tampered ledger");

        // Chain verification should fail (hash mismatch), and checkpoint verification should fail (digest mismatch).
        assert!(verify_chain(&log_path_s).is_err());
        assert!(verify_checkpoints(&log_path_s).is_err());
    }
}
