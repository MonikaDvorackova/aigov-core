# Local checks & health

Practical commands to validate an audit endpoint or the documentation/dashboard workspace from your laptop.

## Quick probes

```try
title: Audit HTTP liveness and readiness
what: Point GOVAI_AUDIT_BASE_URL at Docker, KIND, or a hosted pilot. Keys optional for /health only.
mode: api
env: export GOVAI_AUDIT_BASE_URL=http://127.0.0.1:8080
tabs:
  - label: health
    command: |
      curl -fsS "$GOVAI_AUDIT_BASE_URL/health"
    expected: 200 — process started
  - label: ready
    command: |
      curl -sS "$GOVAI_AUDIT_BASE_URL/ready"
    expected: 200 when dependencies OK; 503 when migrations/DB block traffic
  - label: status
    command: |
      curl -fsS "$GOVAI_AUDIT_BASE_URL/status"
    expected: build/policy diagnostics JSON
next_href: /docs/api-reference
next_label: API reference
```

### Auth smoke (when you have a key)

```try
title: Authenticated compliance summary
what: Confirms GOVAI_API_KEY is accepted before debugging BLOCKED/INVALID.
mode: api
env: |
  export GOVAI_AUDIT_BASE_URL=https://audit.example.com
  export GOVAI_API_KEY=your_key
  export GOVAI_RUN_ID=your_run_id
tabs:
  - label: curl
    command: |
      curl -fsS -H "Authorization: Bearer $GOVAI_API_KEY" \
        "$GOVAI_AUDIT_BASE_URL/compliance-summary?run_id=$GOVAI_RUN_ID" | jq '{verdict}'
    expected: verdict key present (VALID, INVALID, or BLOCKED)
next_href: /help/troubleshooting
next_label: Troubleshooting
```

## Repository diagnostics

```try
title: OSS diagnostics and readiness scripts
what: Matches maintenance targets used before merging governance-sensitive changes.
mode: local
tabs:
  - label: oss-diagnostics
    command: make oss-diagnostics
    expected: Reported checks PASS for your area
  - label: enterprise-readiness
    command: make enterprise-readiness-check
    expected: PASS when enterprise pack is configured locally
  - label: docs-links
    command: make docs-links-strict
    expected: No broken relative Markdown links under docs/
  - label: rust-tests
    command: cargo test -q
    expected: test result: ok
  - label: python
    command: python3 -m compileall -q python/aigov_py
    expected: Silent success (syntax check)
next_href: /docs/contributing
next_label: Contributing
```

## Dashboard build

```try
title: Build public docs / help dashboard
what: Run after editing TSX under dashboard/app/help or markdown preprocessors.
mode: local
tabs:
  - label: install+build
    command: |
      cd dashboard
      npm ci
      npm run build
    expected: Compiled successfully
next_href: /help/troubleshooting
next_label: If build fails
```

## Route catalog

```docs
preset: api-routes
```

## Related

- [Troubleshooting](../tutorials/debugging-failed-gate.md)
- [Deployment](../hosted-backend-deployment.md)
