//! File-backed [`LedgerView`] for policy ingest gates.

use crate::audit_store;
use crate::policy_engine::LedgerView;
use crate::schema::EvidenceEvent;

pub struct FileLedgerView<'a> {
    log_path: &'a str,
}

impl<'a> FileLedgerView<'a> {
    pub fn new(log_path: &'a str) -> Self {
        Self { log_path }
    }
}

impl LedgerView for FileLedgerView<'_> {
    fn iter_events_for_run<'b>(
        &'b self,
        run_id: &'b str,
    ) -> Box<dyn Iterator<Item = EvidenceEvent> + 'b> {
        let events = match audit_store::scan_ledger_records(self.log_path) {
            Ok((records, _)) => records
                .into_iter()
                .filter_map(|rec| serde_json::from_str::<EvidenceEvent>(&rec.event_json).ok())
                .filter(|ev| ev.run_id == run_id)
                .collect::<Vec<_>>(),
            Err(_) => Vec::new(),
        };
        Box::new(events.into_iter())
    }
}
