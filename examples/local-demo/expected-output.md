# Expected local demo output (illustrative)

Values depend on your environment. When the stack is healthy you should see:

## Python harness (`make local-demo`)

- Table rows for **`GET /health`**, **`GET /ready`**, **`GET /status`** with HTTP status codes.
- **`## Result`** line ending in **`PASS`** when `/health` and `/ready` are HTTP **200**.
- Exit code **0** on PASS.

When Docker is not running:

- **`FAIL`** in the result section and **actionable** commands (`docker compose up`, `make audit_bg`, `curl …/ready`).
- Exit code **1** when the TCP/HTTP connection fails entirely.

When the process listens but Postgres is not ready:

- `/health` may still be **200** while `/ready` is **503** or non-200 — harness exits **2** and prints troubleshooting hints.

## curl script (`make local-demo-curl`)

- Printed HTTP status lines from curl’s `-w` format.
- First bytes of each JSON body for quick visual inspection.
