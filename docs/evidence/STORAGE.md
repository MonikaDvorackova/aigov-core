# Evidence storage

Evidence bundles are stored outside Git as immutable artifacts.

This repository stores only human readable audit reports under docs/reports.  
Each report contains a bundle_sha256 value which is the cryptographic reference to the evidence bundle.

## Default storage backend

GitHub Releases assets.

Each evidence bundle is uploaded as a release asset.

- Release tag: run-<run_id>
- Asset filename: <run_id>.json
- Asset content: docs/evidence/<run_id>.json
- Integrity reference: bundle_sha256 in docs/reports/<run_id>.md

## Procedure

1 Generate evidence bundle  
RUN_ID=<run_id> make bundle  

This creates  
docs/evidence/<run_id>.json  

2 Upload bundle as release asset  
Create a GitHub Release with tag  
run-<run_id>  

Attach  
docs/evidence/<run_id>.json  

3 Verify integrity  
Compute sha256 of the uploaded file and compare it with  
bundle_sha256 in docs/reports/<run_id>.md  

They must match.
