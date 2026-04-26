---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Interfaces

Use this section when the question is what another package, tool, or operator
can safely rely on from `bijux-canon-agent`: commands, HTTP routes, schemas,
config surfaces, orchestration artifacts, trace outputs, and public imports.

This package has unusually high contract pressure because callers do not only
invoke it; they also inspect what it orchestrated. Trace files, result
artifacts, and schema-backed API shapes are part of what readers may depend on
when they assess agent behavior.

## Visual Summary

```mermaid
flowchart LR
    cli["CLI entrypoints and replay helpers"]
    api["HTTP routes and OpenAPI schemas"]
    config["operator config and defaults"]
    artifacts["run results, traces, and emitted artifacts"]
    imports["public Python imports"]
    reader["reader question<br/>which agent surfaces are real contracts?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class cli,page reader;
    class api,config positive;
    class artifacts,imports anchor;
    cli --> reader
    api --> reader
    config --> reader
    artifacts --> reader
    imports --> reader
```

## Start Here

- open [CLI Surface](cli-surface.md) for terminal-facing commands and replay
  entrypoints
- open [API Surface](api-surface.md) when the contract is HTTP-facing rather
  than CLI-facing
- open [Artifact Contracts](artifact-contracts.md) and
  [Data Contracts](data-contracts.md) when trace or result shape matters more
  than invocation syntax

## Pages In This Section

- [CLI Surface](cli-surface.md)
- [API Surface](api-surface.md)
- [Configuration Surface](configuration-surface.md)
- [Data Contracts](data-contracts.md)
- [Artifact Contracts](artifact-contracts.md)
- [Entrypoints and Examples](entrypoints-and-examples.md)
- [Operator Workflows](operator-workflows.md)
- [Public Imports](public-imports.md)
- [Compatibility Commitments](compatibility-commitments.md)

## Use This Section When

- you need to know whether a command, route, trace file, config surface, or
  import is meant to be stable
- a change may affect downstream orchestration expectations or trace readers
- a reviewer needs to separate explicit interfaces from incidental visibility

## Do Not Use This Section When

- the main question is why the behavior belongs in the agent layer at all
- the concern is mostly structural rather than contract-facing
- the issue is procedural or proof-oriented rather than about supported surfaces

## Read Across The Package

- open [Foundation](../foundation/index.md) for package purpose and ownership
- open [Architecture](../architecture/index.md) for the structural seams behind
  the public surfaces
- open [Operations](../operations/index.md) for setup, diagnostics, and release
  procedures
- open [Quality](../quality/index.md) for compatibility evidence and review
  pressure

## Concrete Anchors

- `src/bijux_canon_agent/interfaces/cli/entrypoint.py` for CLI entrypoints
- `src/bijux_canon_agent/api/v1` for HTTP routes and schema-backed handlers
- `src/bijux_canon_agent/config` for operator configuration surfaces
- `src/bijux_canon_agent/traces` and `interfaces/cli/result_artifacts.py` for
  trace and artifact contracts

## Reader Takeaway

Use `Interfaces` to judge whether a dependency on the agent layer is
defensible. The bar is not only that a command exists, but that commands,
schemas, traces, artifacts, examples, and tests all agree about what the
orchestration surface really promises.

## Purpose

This page introduces the agent interfaces handbook and routes readers to the
pages that explain commands, APIs, artifacts, imports, and compatibility
commitments.
