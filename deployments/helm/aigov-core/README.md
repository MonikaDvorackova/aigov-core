# Helm chart: `aigov-core`

Self-hosted **AIGov Core** (`aigov_audit`) ledger runtime.

## Install

```bash
helm upgrade --install aigov-core ./deployments/helm/aigov-core
```

## Compatibility note (repository rename)

The chart was previously named **`govai-core`** (directory, chart `name`, and default Kubernetes labels). After the GitHub repository rename to **`aigov-core`**, use this chart name for new installs.

Existing clusters that installed `helm release` / namespace **`govai-core`** continue to work until you migrate releases manually. GitHub redirects `MonikaDvorackova/govai-core` → `MonikaDvorackova/aigov-core` for git operations only; Helm release names are not redirected automatically.
