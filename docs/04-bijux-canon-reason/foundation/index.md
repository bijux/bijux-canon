---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Foundation

Use this section when you need the durable answer to a simple question: why
does `bijux-canon-reason` exist as its own package between retrieval below and
agent or runtime control above?

This package is where evidence stops being only retrievable and starts becoming
arguable. It owns planning, claim formation, verification, and the traceable
artifacts that let a reviewer inspect what the reasoning layer concluded and
why.

## Visual Summary

```mermaid
flowchart LR
    evidence["retrieved evidence and corpus views"]
    planning["planning intent and reasoning IR"]
    claims["claims, supports, and insufficiency handling"]
    verify["verification and provenance checks"]
    traces["reasoning traces and durable artifacts"]
    handoff["agent and runtime consume inspected output"]
    reader["reader question<br/>what belongs in the reasoning layer?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class evidence,page reader;
    class planning,claims,verify positive;
    class traces,handoff anchor;
    evidence --> planning --> claims --> verify --> traces --> handoff
    planning --> reader
    claims --> reader
    verify --> reader
```

## Start Here

- open [Package Overview](package-overview.md) for the shortest description of
  the package role
- open [Ownership Boundary](ownership-boundary.md) when the question is whether
  logic belongs in retrieval, reasoning, agent orchestration, or runtime
- open [Lifecycle Overview](lifecycle-overview.md) when you need the
  end-to-end shape from evidence intake to verified reasoning output

## Pages In This Section

- [Package Overview](package-overview.md)
- [Scope and Non-Goals](scope-and-non-goals.md)
- [Ownership Boundary](ownership-boundary.md)
- [Repository Fit](repository-fit.md)
- [Capability Map](capability-map.md)
- [Domain Language](domain-language.md)
- [Lifecycle Overview](lifecycle-overview.md)
- [Dependencies and Adjacencies](dependencies-and-adjacencies.md)
- [Change Principles](change-principles.md)

## Use This Section When

- you need the package role before looking at modules, commands, or tests
- you are checking whether a behavior is really reasoning rather than retrieval,
  orchestration, or runtime governance
- a reader needs one page that explains why this package exists without reading
  the whole tree

## Do Not Use This Section When

- the real question is where a module lives or how control flows through code
- you are deciding whether a CLI, API, schema, or artifact is a supported
  contract
- the main concern is operating the package or proving a change is safe

## Read Across The Package

- open [Architecture](../architecture/index.md) for module boundaries,
  execution flow, and persistence seams
- open [Interfaces](../interfaces/index.md) for CLI, API, trace, and schema
  contracts
- open [Operations](../operations/index.md) for install, replay, diagnostics,
  and release procedures
- open [Quality](../quality/index.md) for proof surfaces, invariants, and known
  limitations

## Concrete Anchors

- `packages/bijux-canon-reason` as the package root
- `packages/bijux-canon-reason/src/bijux_canon_reason` as the import boundary
- `packages/bijux-canon-reason/tests` as the package proof surface

## Reader Takeaway

`Foundation` should leave no doubt about the package boundary: retrieval finds
evidence, reasoning turns it into inspectable claims and checks, agent
coordinates multi-step work, and runtime decides what becomes durable and
acceptable.

## Purpose

This page introduces the reasoning foundation handbook and routes readers to
the pages that explain purpose, scope, vocabulary, lifecycle, and boundaries.
