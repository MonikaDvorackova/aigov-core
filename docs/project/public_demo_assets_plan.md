# GovAI Public Demo Assets Plan

## Purpose

This document defines the public demo assets needed to improve GovAI adoption.

Demo assets should make the value of GovAI visible within seconds. They should help users, contributors, enterprise evaluators, investors, and researchers understand what GovAI does without reading the full codebase.

## Goals

The demo assets should show:

1. How GovAI runs locally
2. How a compliance gate passes
3. How a missing approval blocks a workflow
4. How evidence digest continuity is verified
5. How audit records are produced
6. How the hosted compliance gate is used
7. How GovAI differs from ordinary CI checks

## Recommended Assets

## 1. README Screenshot

A static screenshot showing the main GovAI compliance flow.

The screenshot should be placed near the top of the README after the project introduction.

Acceptance criteria:

1. The screenshot is clear and readable
2. The screenshot shows a successful governance flow
3. The screenshot reinforces the decision level auditability message

## 2. Terminal Recording

A short terminal recording should show the local demo running from setup to verification.

Recommended flow:

1. Clone repository
2. Start local services
3. Submit evidence
4. Run verification
5. Show final verdict

Acceptance criteria:

1. The recording is short
2. The commands are readable
3. The final verdict is visible
4. The flow can be reproduced from documentation

## 3. Failing Gate GIF

A short GIF should show GovAI blocking an incomplete workflow.

Recommended failure case:

1. Missing approval
2. Missing evidence
3. Digest mismatch

Acceptance criteria:

1. The blocked result is obvious
2. The failure reason is visible
3. The GIF communicates fail closed semantics clearly

## 4. Architecture Diagram Preview

A compact diagram preview should show the core GovAI flow.

Recommended flow:

1. CI or runtime system
2. Evidence bundle
3. GovAI audit service
4. Human approval gate
5. Compliance summary
6. VALID, INVALID, or BLOCKED verdict

Acceptance criteria:

1. The diagram is simple
2. The diagram fits in README
3. The diagram links to deeper architecture documentation

## 5. Hosted Gate Screenshot

A screenshot should show hosted compliance gate usage.

Acceptance criteria:

1. The screenshot avoids exposing secrets
2. The screenshot shows a real workflow result
3. The screenshot supports enterprise credibility

## Asset Locations

Recommended repository locations:

1. docs/assets/screenshots
2. docs/assets/gifs
3. docs/assets/recordings
4. docs/assets/diagrams

## README Integration

The README should eventually include:

1. A short visual overview
2. A local demo screenshot
3. A failing gate example
4. Links to full documentation
5. Links to example repositories

## Tooling Options

Recommended tooling:

1. asciinema for terminal recordings
2. VHS for scripted terminal GIFs
3. Mermaid for lightweight diagrams
4. PNG screenshots for README previews

## Security Requirements

Demo assets must not expose:

1. API keys
2. Customer data
3. Internal tenant identifiers
4. Private billing identifiers
5. Sensitive infrastructure details

## Priority Order

Recommended implementation order:

1. Local demo terminal recording
2. Failing gate GIF
3. README screenshot
4. Architecture diagram preview
5. Hosted gate screenshot

## Acceptance Criteria

This demo asset work is complete when:

1. At least one local demo recording exists
2. At least one blocked workflow example exists
3. README includes at least one visual asset
4. Assets do not expose secrets
5. Documentation links to the assets
6. The demo can be reproduced locally

## Summary

Public demo assets are adoption accelerators. They make GovAI understandable quickly and help convert technical credibility into actual usage, contribution, and enterprise interest.
