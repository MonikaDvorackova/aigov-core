# Break-glass and admin action audit checklist (security program v0)

`SEC_PROGRAM_BREAK_GLASS`

- [ ] Ensure break-glass flows require explicit role grants (`break_glass` product permission) in product RBAC.
- [ ] Log administrative actions to durable audit surfaces (identity audit / ledger as applicable).
- [ ] Time-bound emergency access; revoke after incident closure.
- [ ] Post-incident review: capture commands run, data touched, and approvals.

Related product surface: tenant console RBAC blocks reference `break_glass` in dashboard snapshots.
