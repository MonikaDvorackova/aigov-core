pub fn verify_chain(log_path: &str) -> Result<(), String> {
    // Delegate to the shared ledger verifier (tolerant of trailing partial/corrupted line).
    crate::audit_store::verify_chain(log_path)
}
