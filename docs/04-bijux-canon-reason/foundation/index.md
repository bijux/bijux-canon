---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Foundation

Open this section when you need the durable answer to a simple question: why
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

- open [Package Overview](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/package-overview/) for the shortest description of
  the package role
- open [Ownership Boundary](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/ownership-boundary/) when the question is whether
  logic belongs in retrieval, reasoning, agent orchestration, or runtime
- open [Lifecycle Overview](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/lifecycle-overview/) when you need the
  end-to-end shape from evidence intake to verified reasoning output

## Pages In Foundation

- [Package Overview](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/package-overview/)
- [Scope and Non-Goals](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/scope-and-non-goals/)
- [Ownership Boundary](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/ownership-boundary/)
- [Repository Fit](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/repository-fit/)
- [Capability Map](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/capability-map/)
- [Domain Language](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/domain-language/)
- [Lifecycle Overview](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/lifecycle-overview/)
- [Dependencies and Adjacencies](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/dependencies-and-adjacencies/)
- [Change Principles](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/change-principles/)

## Use Foundation When

- you need the package role before looking at modules, commands, or tests
- you are checking whether a behavior is really reasoning rather than retrieval,
  orchestration, or runtime governance
- a reader needs one page that explains why this package exists without reading
  the whole tree

## Move On When

- the real question is where a module lives or how control flows through code
- you are deciding whether a CLI, API, schema, or artifact is a supported
  contract
- the main concern is operating the package or proving a change is safe

## Read Across The Package

- open [Architecture](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/) for module boundaries,
  execution flow, and persistence seams
- open [Interfaces](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/) for CLI, API, trace, and schema
  contracts
- open [Operations](https://bijux.io/bijux-canon/04-bijux-canon-reason/operations/) for install, replay, diagnostics,
  and release procedures
- open [Quality](https://bijux.io/bijux-canon/04-bijux-canon-reason/quality/) for proof surfaces, invariants, and known
  limitations

## Concrete Anchors

- `packages/bijux-canon-reason` as the package root
- `packages/bijux-canon-reason/src/bijux_canon_reason` as the import boundary
- `packages/bijux-canon-reason/tests` as the package proof surface

## Why Open Foundation

`Foundation` leaves leave no doubt about the package boundary: retrieval finds
evidence, reasoning turns it into inspectable claims and checks, agent
coordinates multi-step work, and runtime decides what becomes durable and
acceptable.

## What You Get

Open this page when you need the purpose, scope, vocabulary, lifecycle, and boundary
route into `bijux-canon-reason` before you move on to structure, contracts,
operations, or proof.
