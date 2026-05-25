#[tokio::main]
async fn main() {
    if let Err(e) = aigov_audit::run().await {
        eprintln!("aigov_audit failed: {e}");
        std::process::exit(1);
    }
}
