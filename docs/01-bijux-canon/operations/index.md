---
title: Operations
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Operations

The operations section explains how the repository is run, reviewed, and kept
coherent after the foundation has already made the ownership model clear.

These pages are about repeatable repository work rather than package-local
behavior. They should help a maintainer move from a question about setup,
validation, release flow, automation, or review posture to the concrete files
that carry that work today. The point is not to create ceremony. The point is
to keep operational memory checked in and inspectable.

## Visual Summary

```mermaid
flowchart LR
    reader["reader question<br/>how is shared repository work carried out?"]
    setup["setup and contributor workflow"]
    validation["testing, validation, and schema governance"]
    release["release and artifact handling"]
    review["review posture and change management"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    class reader page;
    class setup,validation,release positive;
    class review caution;
    reader --> setup
    reader --> validation
    reader --> release
    reader --> review
```

## Start Here

- open [Testing and Validation](testing-and-validation.md) when the question is
  what shared proof must run before accepting a change
- open [Contributor Workflows](contributor-workflows.md) for the shortest route
  through normal repository work
- open [Release and Versioning](release-and-versioning.md) when the question is
  tag, package, or published artifact behavior
- open [Automation Surfaces](automation-surfaces.md) when the real issue is
  which shared automation owns the current action

## Pages in This Section

- [Local Development](local-development.md)
- [Testing and Validation](testing-and-validation.md)
- [Release and Versioning](release-and-versioning.md)
- [API and Schema Governance](api-and-schema-governance.md)
- [Contributor Workflows](contributor-workflows.md)
- [Automation Surfaces](automation-surfaces.md)
- [Artifact Governance](artifact-governance.md)
- [Review Expectations](review-expectations.md)
- [Change Management](change-management.md)

## Use This Section When

- you are performing repository-wide work instead of one package-local change
- you need the operational truth for shared automation, release, or validation
- you are checking whether a proposed workflow is explicit enough to maintain

## Do Not Use This Section When

- the real question is still why the split exists or where authority changes
  hands
- you already know the issue belongs in one package's local operations docs
- you need maintainer-helper implementation detail rather than repository
  procedure

## Concrete Anchors

- `Makefile` and `makes/` for shared command entrypoints
- `.github/workflows/` for repository-wide automation and release execution
- `apis/` for schema governance surfaces that affect shared review
- [Testing and Validation](testing-and-validation.md) and
  [Artifact Governance](artifact-governance.md) for the highest-cost shared
  review surfaces

## Read Across The Repository

- open [Foundation](../foundation/index.md) when an operational problem is
  really a boundary problem
- open [Maintainer Handbook](../../07-bijux-canon-maintain/index.md) when the
  question becomes workflow implementation, drift tooling, or maintainer helper
  code
- open the owning package handbook when the operation is no longer truly shared

## Reader Takeaway

Use `Operations` when the issue is how the repository behaves as a shared
system. If a workflow only makes sense through private habit, CI archaeology,
or package-local tribal knowledge, the shared operational story is not yet
strong enough.

## Purpose

This page gives maintainers the shortest route into the repository’s operational
guidance without forcing them to infer it from CI logs or Make targets first.
