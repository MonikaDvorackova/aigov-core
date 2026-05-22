# GovAI Open Source Adoption Checklist

## Purpose

This checklist tracks the remaining work needed to make GovAI easier to adopt, evaluate, and contribute to as a public open source governance platform.

## Core Repository Maturity

- Contributor guide exists
- Security policy exists
- Pull request template exists
- CODEOWNERS exists
- Public roadmap exists
- Label taxonomy exists
- Milestones exist
- Maintainer guide exists
- Release checklist exists
- Compatibility policy exists
- Threat model exists
- CHANGELOG exists

## Documentation Readiness

- README includes an OSS onboarding section
- Project roadmap is documented
- Glossary is documented
- Project structure is documented
- Architecture diagrams are documented
- Local demo instructions are documented
- Documentation website plan exists
- Tutorials and blog plan exists

## Adoption Assets

- Docker Compose local demo exists
- Public demo assets plan exists
- Example repositories plan exists
- Terminal recording is planned
- Failing gate GIF is planned
- README screenshot is planned
- Architecture preview asset is planned

## Release Engineering

- Changelog exists
- Release checklist exists
- Release notes automation plan exists
- Semantic versioning expectations are documented
- Deprecation expectations are documented
- Compatibility review expectations are documented

## Security and Trust

- Threat model exists
- Trust assumptions are documented
- Protected assets are documented
- Threat scenarios are documented
- Mitigations are documented
- Residual risks are documented

## Ecosystem Expansion

- Example repositories are planned
- Tutorials are planned
- Blog posts are planned
- Documentation website is planned
- Public demo assets are planned
- Conference talk themes are planned for future work
- Pilot customer materials are planned for future work

## Immediate Next Priorities

1. Merge the compatibility policy
2. Merge the threat model
3. Merge the changelog
4. Merge adoption planning documents
5. Build the documentation website
6. Create the first example repository
7. Add public demo assets to the README

## Definition of Done

GovAI reaches a strong open source adoption baseline when:

1. A new user can understand the project from the README
2. A new user can run a local demo
3. A new user can see a passing and blocked governance flow
4. A contributor can find a good first issue
5. A maintainer can prepare a release predictably
6. An enterprise evaluator can understand the threat model
7. An adopter can understand compatibility expectations
8. Public examples show realistic integration paths

## Summary

GovAI already has a strong open source foundation. The remaining work is mostly adoption acceleration: documentation website, example repositories, public demo assets, tutorials, and release process automation.

## OSS developer experience gap fill (tracked completions)

Items completed by the OSS developer experience gap-fill work:

- [x] Root code of conduct (`CODE_OF_CONDUCT.md`)
- [x] Local environment variable template (`.env.example`, placeholders only)
- [x] Expanded GitHub issue templates (`feature_request`, `question`, `config.yml` security link)
- [x] Downstream CI example snippet (`examples/ci/govai-check.yml`, example-only path)
- [x] Local development walkthrough (`docs/project/local_development.md`)
- [x] Examples index + READMEs (`examples/README.md`, `examples/ci`, `examples/runtime-evaluate`, `examples/evidence-pack`)
- [x] Developer onboarding architecture flow (`docs/architecture/developer_onboarding_flow.md`)
- [x] Contributor workflow doc (`docs/project/contributor_workflow.md`)
- [x] Read-only local demo harness (`scripts/run_local_demo.py`, `make local-demo`, `examples/local-demo/`)
- [x] Public documentation on **govbase.dev** (`dashboard/` `/docs` + `/help`, canonical Markdown in `docs/`)
