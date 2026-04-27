---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Interfaces

Open this section when the question is contractual: which reasoning entrypoints, artifacts, payloads, and imports are real promises rather than merely visible implementation details.

## Contract Surface

Reason interfaces are reviewer-facing contracts. They expose how callers start
a reasoning run, what artifact shapes come back, how provenance and checks are
serialized, and which public imports are stable enough for downstream packages
to use without copying internal policy.

```mermaid
flowchart LR
    caller["caller or reviewer"]
    cli["CLI surface"]
    api["API surface"]
    artifacts["claims and checks"]
    serialization["serialized outputs"]
    imports["public imports"]
    schema["tracked schema"]
    downstream["agent or runtime"]

    caller --> cli --> artifacts
    caller --> api --> artifacts
    artifacts --> serialization --> downstream
    imports --> artifacts
    api --> schema
```

Reason interfaces matter because other tools and reviewers consume the meaning
they emit. The important promise is not only that a run can be started, but
that claims, checks, and provenance can be serialized and reused without
copying hidden package policy.

## Read These First

- open [Data Contracts](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/data-contracts/) first when the issue is about claim, check, or provenance payload shape
- open [Artifact Contracts](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/artifact-contracts/) when downstream tools depend on stable reasoning outputs
- open [Compatibility Commitments](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/compatibility-commitments/) when a reasoning-surface change may break reviewers or callers

## Contract Risk

The main contract risk here is letting reviewer-facing reasoning artifacts drift without naming which shapes and entrypoints are actually supported.

## First Proof Check

- `packages/bijux-canon-reason/src/bijux_canon_reason/interfaces` for CLI, serialization, and access guard boundaries
- `packages/bijux-canon-reason/src/bijux_canon_reason/api/v1` for HTTP route and OpenAPI model surfaces
- `apis/bijux-canon-reason/v1/schema.yaml` for tracked schema visibility
- `packages/bijux-canon-reason/tests` for claim, provenance, and compatibility evidence


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

## Leave This Section When

- leave for [Foundation](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/) when the contract dispute is really a package-boundary dispute
- leave for [Architecture](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/) when a surface question reveals structural drift underneath it
- leave for [Operations](https://bijux.io/bijux-canon/04-bijux-canon-reason/operations/) or [Quality](https://bijux.io/bijux-canon/04-bijux-canon-reason/quality/) when the boundary is clear and the question becomes execution or proof

## Design Pressure

If downstream tools treat a reasoning artifact as stable but this page does not
name it, the contract has already escaped the docs. The interface surface has
to state which outputs are intentionally reusable.
