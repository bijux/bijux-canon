---
title: Migration
audience: mixed
type: index
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Migration

Use this section to understand how legacy names should be retired
responsibly instead of merely coexisting forever.

It covers the full transition path: how canonical package names replace legacy
names, what continuity must be preserved while both exist, what validation must
run during the overlap, and what evidence is required before a compatibility
package can disappear.

## Pages In This Section

- [Compatibility Overview](https://bijux.io/bijux-canon/08-compat-packages/migration/compatibility-overview/)
- [Migration Guidance](https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/)
- [Repository Consolidation](https://bijux.io/bijux-canon/08-compat-packages/migration/repository-consolidation/)
- [Canonical Targets](https://bijux.io/bijux-canon/08-compat-packages/migration/canonical-targets/)
- [Dependency Continuity](https://bijux.io/bijux-canon/08-compat-packages/migration/dependency-continuity/)
- [Release Policy](https://bijux.io/bijux-canon/08-compat-packages/migration/release-policy/)
- [Validation Strategy](https://bijux.io/bijux-canon/08-compat-packages/migration/validation-strategy/)
- [Retirement Conditions](https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/)
- [Retirement Playbook](https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-playbook/)

## Open This Section When

- you are planning or reviewing a migration away from legacy package names
- you need the shared rules for compatibility release and retirement decisions
- you need the future posture of the compatibility layer rather than its current catalog entry

## Open Another Section When

- the only open question is which exact legacy surface is still preserved
- the concern is already about current product behavior in a canonical package
- the issue belongs to maintainer automation rather than compatibility policy

## Start Here

- open [Canonical Targets](https://bijux.io/bijux-canon/08-compat-packages/migration/canonical-targets/) when the first need is the exact new package name
- open [Dependency Continuity](https://bijux.io/bijux-canon/08-compat-packages/migration/dependency-continuity/) when requirements, imports, or command preservation are the current risk
- open [Validation Strategy](https://bijux.io/bijux-canon/08-compat-packages/migration/validation-strategy/) when the migration must be proven through tests, metadata, or release checks
- open [Retirement Conditions](https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/) or [Retirement Playbook](https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-playbook/) when the preserved bridge might be ready to disappear

## Concrete Anchors

- `packages/compat-*` for the shipping compatibility bridges
- compatibility package `README.md` files for explicit canonical targets
- canonical package docs under `docs/02-bijux-canon-ingest/` through `docs/06-bijux-canon-runtime/` for current behavior

## Migration Standard

Migration is complete only when preserved names are no longer needed for real
dependent environments and the canonical package can carry the workload alone
without hidden breakage. Until then, continuity and validation must stay more
important than aesthetic cleanup.
