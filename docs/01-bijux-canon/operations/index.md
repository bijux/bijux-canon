---
title: Operations
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Operations

Use the operations section when the ownership model is already clear and you
need the repeatable repository procedure that follows from it. These pages
cover local setup, validation, schema review, artifact handling, release
flow, and change acceptance across the package set.

## Start Here

- open [Contributor Workflows](https://bijux.io/bijux-canon/01-bijux-canon/operations/contributor-workflows/) for the shortest route through normal repository work
- open [Testing and Validation](https://bijux.io/bijux-canon/01-bijux-canon/operations/testing-and-validation/) when you need to know which shared proof must run before acceptance
- open [API and Schema Governance](https://bijux.io/bijux-canon/01-bijux-canon/operations/api-and-schema-governance/) when the concern is contract drift or reviewed schema change
- open [Release and Versioning](https://bijux.io/bijux-canon/01-bijux-canon/operations/release-and-versioning/) when the concern is tag behavior, package publication, or release discipline
- open [Automation Surfaces](https://bijux.io/bijux-canon/01-bijux-canon/operations/automation-surfaces/) when you need to know which shared root automation owns the current action

## Pages In This Section

- [Local Development](https://bijux.io/bijux-canon/01-bijux-canon/operations/local-development/)
- [Testing and Validation](https://bijux.io/bijux-canon/01-bijux-canon/operations/testing-and-validation/)
- [Release and Versioning](https://bijux.io/bijux-canon/01-bijux-canon/operations/release-and-versioning/)
- [API and Schema Governance](https://bijux.io/bijux-canon/01-bijux-canon/operations/api-and-schema-governance/)
- [Contributor Workflows](https://bijux.io/bijux-canon/01-bijux-canon/operations/contributor-workflows/)
- [Automation Surfaces](https://bijux.io/bijux-canon/01-bijux-canon/operations/automation-surfaces/)
- [Artifact Governance](https://bijux.io/bijux-canon/01-bijux-canon/operations/artifact-governance/)
- [Review Expectations](https://bijux.io/bijux-canon/01-bijux-canon/operations/review-expectations/)
- [Change Management](https://bijux.io/bijux-canon/01-bijux-canon/operations/change-management/)

## Open This Section When

- you are performing repository-wide work instead of one package-local change
- you need the operational truth for shared automation, release, or validation
- you are checking whether a proposed workflow is explicit enough to maintain

## Open Another Section When

- the real question is still why the split exists or where authority changes
  hands
- you already know the issue belongs in one package's local operations docs
- you need maintainer-helper implementation detail rather than repository
  procedure

## Concrete Anchors

- `Makefile` and `makes/` for shared command entrypoints
- `.github/workflows/` for repository-wide automation and release execution
- `apis/` for schema governance surfaces that affect shared review
- [Testing and Validation](https://bijux.io/bijux-canon/01-bijux-canon/operations/testing-and-validation/) and
  [Artifact Governance](https://bijux.io/bijux-canon/01-bijux-canon/operations/artifact-governance/) for the highest-cost shared
  review surfaces

## Read Across The Repository

- open [Foundation](https://bijux.io/bijux-canon/01-bijux-canon/foundation/) when an operational problem is really a boundary problem
- open the [Maintainer Handbook](https://bijux.io/bijux-canon/07-bijux-canon-maintain/) when the next step is workflow implementation, drift tooling, or maintainer helper code
- open the owning package handbook when the operation is no longer truly shared

## Operational Standard

Shared procedure must be discoverable from checked-in rules, commands, and
workflow files. If a repository-wide action still depends on CI archaeology or
private habit, the operational surface is not documented strongly enough yet.
