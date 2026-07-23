# Contributor License Agreements (CLA)

## Overview

To protect contributors, users, and AIMLGov, all external code contributions to this Covered Project require acceptance of the applicable Contributor License Agreement (CLA).

The CLA provides AIMLGov with the legal rights necessary to review, maintain, distribute, and license Contributions while allowing contributors to retain ownership of their intellectual property.

Signing a CLA **does not transfer copyright ownership** to AIMLGov.

---

## Which CLA applies?

### Individual Contributor License Agreement (ICLA)

The Individual CLA applies to individual developers, students, researchers, independent contractors contributing in a personal capacity, and any contributor who is not contributing on behalf of an organization.

Location: `legal/published/individual-contributor-license-agreement.md`

### Corporate Contributor License Agreement (CCLA)

The Corporate CLA applies where Contributions are made on behalf of companies, universities, research institutions, government bodies, non-profits, or any other legal entity.

Location: `legal/published/corporate-contributor-license-agreement.md`

---

## How to contribute

1. Fork the repository (or use a branch with write access).
2. Create a feature branch from `staging`.
3. Accept the applicable CLA.
4. Open a pull request targeting `staging`.
5. Wait for automated CLA verification (`CLAAssistant`).
6. Address review comments.
7. After approval, maintainers may merge.

---

## GitHub CLA Assistant (this repository)

Pull requests (including those targeting `staging` or `main`) are checked by the **CLA Assistant** workflow (`.github/workflows/cla.yml`). The pull request checklist checkbox is a contributor reminder only; it is **not** legal acceptance.

**Individuals** sign by posting this exact pull request comment:

```text
I have read the CLA Document and I hereby sign the CLA
```

Signatures are stored in `signatures/version1/cla.json` on the `main` branch (created automatically on first signature). Comment `recheck` to re-run verification.

**Organizations** execute the Corporate CLA separately and maintain Authorized Contributors (Schedule A). After AIMLGov accepts a Corporate CLA, maintainers add those GitHub usernames to the workflow `allowlist` in `.github/workflows/cla.yml`.

Maintainers listed in the allowlist (and named bot accounts such as `dependabot[bot]` and `github-actions[bot]`) are not required to sign for routine maintenance commits.

Signature commits use the workflow `GITHUB_TOKEN`. If `main` is branch-protected, configure protection so `github-actions[bot]` can update `signatures/version1/cla.json` (or store signatures on an unprotected branch).

---

## Frequently asked questions

### Do I keep the copyright to my Contributions?

Yes. Except for the licenses granted under the applicable CLA, contributors retain ownership of their Contributions.

### Do I need to sign the CLA for every Pull Request?

No. Once accepted, the CLA remains effective according to its terms.

### I am contributing on behalf of my employer.

Use the Corporate CLA and ensure you are listed as an Authorized Contributor before opening code pull requests.
