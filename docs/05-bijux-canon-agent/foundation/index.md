---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Foundation

Use this section when you need the durable answer to a simple question: why
does `bijux-canon-agent` exist between reasoning outputs below and runtime
authority above?

This package is where one reasoning-capable step becomes coordinated work. It
owns role-based agents, pipeline control, trace-bearing execution flow, and the
rules that keep orchestration inspectable instead of magical.

## Visual Summary

```mermaid
flowchart LR
    reason["reasoned steps and evidence-backed outputs"]
    roles["role-local agents and capability boundaries"]
    pipeline["pipeline control and orchestration flow"]
    traces["trace records and replay-aware execution artifacts"]
    runtime["runtime consumes governed run outcomes"]
    reader["reader question<br/>what belongs in the agent layer?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class reason,page reader;
    class roles,pipeline positive;
    class traces,runtime anchor;
    reason --> roles --> pipeline --> traces --> runtime
    roles --> reader
    pipeline --> reader
    traces --> reader
```

## Start Here

- open [Package Overview](package-overview.md) for the shortest explanation of
  the orchestration role
- open [Ownership Boundary](ownership-boundary.md) when the question is whether
  behavior belongs in reasoning, agent coordination, or runtime governance
- open [Lifecycle Overview](lifecycle-overview.md) when you need the package
  story from agent input through traceable output

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

- you need the package role before looking at APIs, modules, or workflows
- you are deciding whether a feature is orchestration behavior or belongs in a
  lower or higher package
- a reader needs one page that explains why this package exists without reading
  the whole handbook

## Do Not Use This Section When

- the main question is where a module or execution path lives
- you are deciding whether a CLI, API, artifact, or import is a contract
- the issue is procedural or proof-oriented rather than boundary-oriented

## Read Across The Package

- open [Architecture](../architecture/index.md) for module groups, execution
  flow, and dependency direction
- open [Interfaces](../interfaces/index.md) for CLI, API, artifact, and import
  contracts
- open [Operations](../operations/index.md) for setup, diagnostics, and release
  procedures
- open [Quality](../quality/index.md) for trust posture, invariants, and review
  standards

## Concrete Anchors

- `packages/bijux-canon-agent` as the package root
- `packages/bijux-canon-agent/src/bijux_canon_agent` as the import boundary
- `packages/bijux-canon-agent/tests` as the package proof surface

## Reader Takeaway

`Foundation` should leave no doubt about the package boundary: reasoning
produces inspectable content, agent coordination turns that into role-based and
trace-backed workflow behavior, and runtime decides what becomes governed and
durable.

## Purpose

This page introduces the agent foundation handbook and routes readers to the
pages that explain purpose, scope, vocabulary, lifecycle, and boundaries.
