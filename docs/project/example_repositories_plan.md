# GovAI Example Repositories Plan

## Purpose

This document defines the planned public example repositories for GovAI.

Example repositories are adoption assets. They should show how GovAI is used in realistic AI, CI/CD, and runtime governance workflows.

## Goals

The example repositories should help users:

- Understand GovAI quickly
- Run working integrations
- Copy production-oriented patterns
- Evaluate decision-level auditability
- Understand fail-closed governance
- Integrate GovAI into existing AI workflows

## Planned Example Repositories

## 1. govai-github-actions-example

This repository should demonstrate GovAI in a GitHub Actions compliance workflow.

It should include:

- Minimal Python project
- GitHub Actions workflow
- GovAI compliance gate
- Evidence bundle generation
- Human approval example
- Passing and failing examples

Acceptance criteria:

- A new user can clone the repo and understand the workflow within minutes
- The workflow clearly demonstrates VALID, INVALID, and BLOCKED outcomes
- The README explains each step

## 2. govai-runtime-governance-demo

This repository should demonstrate runtime governance checks.

It should include:

- Minimal API service
- Runtime decision event submission
- Audit server integration
- Example policy decision
- Example blocked decision

Acceptance criteria:

- The demo can run locally
- Runtime events are visible in the audit flow
- The README explains the governance boundary

## 3. govai-langchain-example

This repository should demonstrate GovAI with an LLM application workflow.

It should include:

- Simple LangChain application
- Decision logging
- Evidence bundle creation
- Governance check before deployment
- Example unsafe or incomplete workflow blocked by GovAI

Acceptance criteria:

- The example is understandable without deep LangChain expertise
- The governance value is visible
- The README explains how GovAI complements LLM app development

## 4. govai-mlflow-example

This repository should demonstrate GovAI with model lifecycle tracking.

It should include:

- Minimal ML training workflow
- MLflow tracking
- Evaluation artifact
- GovAI evidence bundle
- Approval gate
- Promotion decision

Acceptance criteria:

- The example shows how model tracking and governance differ
- GovAI validates decision-level evidence, not only model metrics
- The README explains the auditability gap

## Repository Standards

Each example repository should include:

- README.md
- LICENSE
- Minimal working code
- GitHub Actions workflow where relevant
- Clear setup instructions
- Expected output
- Troubleshooting section
- Link back to the main GovAI repository

## Priority Order

Recommended implementation order:

1. govai-github-actions-example
2. govai-runtime-governance-demo
3. govai-langchain-example
4. govai-mlflow-example

## Maintenance Model

Example repositories should be treated as supported adoption assets.

They should be updated when:

- Public APIs change
- CLI behavior changes
- Evidence schemas change
- GitHub Action inputs change
- Documentation links change

## Summary

Example repositories are a critical adoption layer for GovAI. They should demonstrate practical integrations and make the decision-level governance model immediately understandable to users, contributors, and enterprise evaluators.
