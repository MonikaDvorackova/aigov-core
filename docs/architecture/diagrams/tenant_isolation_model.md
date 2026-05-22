# GovAI Tenant Isolation Model

This document describes the tenant isolation model used by GovAI.

## Core rule

Tenant isolation is derived from server-side API key mapping.

Client-provided project headers are metadata only and must not be treated as security boundaries.

## Flow

1. A request arrives with an API key.

2. The server resolves the tenant from the configured API key mapping.

3. Ledger access is scoped to the resolved tenant.

4. Audit events are written only under that tenant context.

5. Queries and exports are restricted to the resolved tenant.

## Text diagram

Incoming request
  ->
API key validation
  ->
Tenant resolution
  ->
Tenant-scoped ledger path
  ->
Tenant-scoped audit write
  ->
Tenant-scoped export or query

## Security invariant

The tenant used for ledger isolation must not be derived from user-controlled headers.

## Non-security metadata

X-GovAI-Project may be used as project metadata, billing context, or display context.

It must not determine ledger isolation.
