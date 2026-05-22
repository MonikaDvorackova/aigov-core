# GovAI High-Level Architecture

```mermaid
flowchart TD

    A[Developer / Runtime System]
    B[GovAI Python SDK / CLI]
    C[Evidence Collection]
    D[Policy Engine]
    E{Governance Verdict}
    F[VALID]
    G[INVALID]
    H[BLOCKED]
    I[Rust Audit Service]
    J[Audit Ledger]
    K[Evidence Export]
    L[Replay Verification]
    M[Human Approval]
    N[CI/CD Pipeline]
    O[Runtime Governance API]

    A --> B
    N --> B
    B --> C
    C --> D
    M --> D
    O --> D

    D --> E
    E --> F
    E --> G
    E --> H

    D --> I
    I --> J
    J --> K
    K --> L
