# Example customer repositories (GovAI integration patterns)

These directories are **documentation-only** blueprints. They are not runnable sub-repositories and do not ship application code, datasets, or model weights.

Use them to explain **how GovAI fits** into common customer stacks: CI gates, RAG pipelines, agent frameworks, experiment tracking, and regulated verticals.

| Example | Primary audience |
| --- | --- |
| [github-actions-example](github-actions-example/README.md) | DevEx / platform engineers wiring CI |
| [rag-example](rag-example/README.md) | ML engineers shipping retrieval systems |
| [langchain-example](langchain-example/README.md) | Application teams using agent frameworks |
| [mlflow-example](mlflow-example/README.md) | MLOps teams tracking runs and promotions |
| [healthcare-example](healthcare-example/README.md) | Compliance-minded teams in healthcare AI |

## Related material

- **Tutorials**: [`../../docs/tutorials/README.md`](../../docs/tutorials/README.md)
- **Benchmark suite (metadata)**: [`../../benchmarks/README.md`](../../benchmarks/README.md)
- **OSS community governance**: [`../../docs/community/maintainer-guide.md`](../../docs/community/maintainer-guide.md)

## Non-goals

- No production-ready Helm charts, Terraform, or cloud-specific IaC in this folder.
- No substitute for your organisation’s security review or legal sign-off.
