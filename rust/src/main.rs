//! Binary wrapper — implementation lives in `lib.rs` (`aigov_audit::run`).

#[tokio::main]
async fn main() {
    if let Err(e) = aigov_audit::run().await {
        eprintln!("Server error: {}", e);
        std::process::exit(1);
    }
}
