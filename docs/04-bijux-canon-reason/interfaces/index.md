---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Interfaces

Open this section when the question is what another package, tool, or operator
can safely rely on from `bijux-canon-reason`: commands, HTTP routes, schema
shapes, trace formats, artifacts, and public imports.

This package carries more contract pressure than an internal helper library
because its outputs are designed to be inspected, replayed, and challenged. A
reasoning trace or verification artifact is not just “something the code wrote”;
it is part of the evidence a later reader may depend on.

## Start Here

- open [CLI Surface](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/cli-surface/) for operator-facing commands and replay
  entrypoints
- open [API Surface](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/api-surface/) when the contract is HTTP-facing rather
  than terminal-facing
- open [Artifact Contracts](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/artifact-contracts/) and
  [Data Contracts](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/data-contracts/) when the durable output shape matters
  more than the call syntax

## Pages In This Section

- [CLI Surface](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/cli-surface/)
- [API Surface](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/api-surface/)
- [Configuration Surface](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/configuration-surface/)
- [Data Contracts](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/data-contracts/)
- [Artifact Contracts](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/artifact-contracts/)
- [Entrypoints and Examples](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/entrypoints-and-examples/)
- [Operator Workflows](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/operator-workflows/)
- [Public Imports](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/public-imports/)
- [Compatibility Commitments](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/compatibility-commitments/)

## Open This Section When

- you need to know whether a command, route, schema, trace file, or import is
  meant to be stable
- a change may affect replayability, artifact reading, or downstream contract
  assumptions
- a reviewer needs to separate explicit interfaces from incidental visibility

## Open Another Section When

- the real question is why the behavior belongs in reasoning at all
- the concern is mainly how the package is organized internally
- the issue is procedural or proof-oriented rather than contract-oriented

## Across This Package

- open [Foundation](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/) for package purpose and ownership
- open [Architecture](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/) for structural seams behind the
  public surfaces
- open [Operations](https://bijux.io/bijux-canon/04-bijux-canon-reason/operations/) for install, replay, and release
  procedures
- open [Quality](https://bijux.io/bijux-canon/04-bijux-canon-reason/quality/) for compatibility evidence and review
  pressure

## Concrete Anchors

- `src/bijux_canon_reason/interfaces/cli` for command entrypoints
- `src/bijux_canon_reason/api/v1` for HTTP routes and models
- `src/bijux_canon_reason/interfaces/serialization` for canonical JSON and
  trace JSONL formats
- `apis/bijux-canon-reason/v1/schema.yaml` for the published schema contract

## Bottom Line

Open this section to judge whether a dependency is defensible. In this package,
the answer is not just “is there a function for it?” but also “can a reviewer
trace the contract through commands, schemas, artifacts, examples, and tests?”

