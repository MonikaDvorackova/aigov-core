# aigov-py

Python package for AIGov Core: CLI (`govai`), audit HTTP client helpers, standards validators, and evidence tooling.

Full repository documentation: [README.md](../README.md).

## Install

Install the published CLI package:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "aigov-py==0.2.1"
```

For repository development, install this package from the checkout:

```bash
cd python
python -m pip install -e ".[dev]"
```

## First command

Confirm that the `govai` console script is available:

```bash
govai --version
```

Expected output:

```text
0.2.1
```

This command does not require a running audit service. Runtime commands such as `govai check`, `govai compliance-summary`, and `govai run demo` need `GOVAI_AUDIT_BASE_URL` and `GOVAI_API_KEY` (or the equivalent CLI flags) when they call the audit API.

## Troubleshooting

- `govai: command not found`: activate the virtual environment where you installed `aigov-py`.
- `No package metadata was found for aigov-py`: install the package instead of only adding the source tree to `PYTHONPATH` (`python -m pip install -e ./python` from the repository root).
- Connection refused or `/ready` is not reachable: start the audit runtime and set `GOVAI_AUDIT_BASE_URL` to its origin.
- `401` or `403` responses: make sure `GOVAI_API_KEY` matches the server-side `GOVAI_API_KEYS` / `GOVAI_API_KEYS_JSON` settings.

More CLI examples are in [docs/cli-reference.md](../docs/cli-reference.md) and the local runtime walkthrough is in [docs/quickstart-5min.md](../docs/quickstart-5min.md).
