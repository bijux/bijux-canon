---
title: Operations
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Operations

The operations section covers the shared procedures that keep the package split
credible after code changes: local workflow, validation, schema review,
artifact handling, release flow, and review discipline.

The main mistake this section should prevent is operational folklore. Shared
work should be discoverable from checked-in commands, workflows, schemas, and
docs instead of from CI archaeology or private maintainer memory.

## Operating Loop

Operations pages should make the shared work loop visible: a contributor
changes a package or root contract, runs the relevant local command, leaves
artifacts in the repository-owned output area, and lets CI repeat the same
intent before release.

```mermaid
flowchart LR
    change["change intent<br/>package, schema, docs, release"]
    local["local workflow<br/>make targets and package checks"]
    artifacts["artifacts/<br/>logs, reports, generated run output"]
    review["review gate<br/>diff, proof, boundary check"]
    ci["CI and release workflows<br/>repeat shared commands"]
    publish["publishable result<br/>package, docs, schema, release"]

    change --> local --> artifacts --> review --> ci --> publish
    change -. schema pressure .-> apis["apis/<br/>checked-in contracts"]
    ci -. workflow source .-> workflows[".github/workflows/<br/>automation truth"]

    classDef page fill:#eef6ff,stroke:#2563eb,color:#153145,stroke-width:2px;
    classDef positive fill:#eefbf3,stroke:#16a34a,color:#173622;
    classDef anchor fill:#f4f0ff,stroke:#7c3aed,color:#47207f;
    classDef action fill:#fff4da,stroke:#d97706,color:#6b3410;
    class change page;
    class local,review,ci positive;
    class artifacts,apis,workflows anchor;
    class publish action;
```

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

- the real question is still why the split exists or where authority changes hands
- you already know the issue belongs in one package's local operations docs
- you need maintainer-helper implementation detail rather than repository procedure

## First Proof Checks

- `Makefile` and `makes/` for shared command entrypoints and routing
- `.github/workflows/` for repository-wide automation and release execution
- `apis/` for schema governance surfaces that affect shared review
- the relevant package handbook once the action stops being truly shared

## Bottom Line

These pages should tell a maintainer what shared procedure to trust, what file
enforces it, and what proof should fail if it drifts. If the workflow still
depends on memory, the repository procedure is not documented strongly enough.
