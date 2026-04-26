---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Interfaces

Open this section when the question is contractual: which index commands, APIs, retrieval outputs, artifacts, and imports callers may treat as stable enough to build on.

## Contract Surface

Index contracts sit between prepared data and evidence consumers. They include
operator commands, HTTP routes, query payloads, execution artifacts, and replay
records. The page should make clear which surfaces are stable promises and
which backend details remain internal.

```mermaid
flowchart LR
    caller["caller or operator"]
    cli["CLI surface<br/>query, ingest, artifact, diagnostics"]
    api["API surface<br/>read, query, mutation routes"]
    request["request contracts<br/>execution plan, budget, scoring"]
    artifact["artifact contracts<br/>result collection and provenance"]
    replay["replay contracts<br/>audit, lineage, drift visibility"]
    consumer["reason or runtime<br/>evidence consumer"]

    caller --> cli --> request
    caller --> api --> request
    request --> artifact --> replay --> consumer
    request -. schema evidence .-> schema["apis/bijux-canon-index/v1/schema.yaml"]

    classDef page fill:#eef6ff,stroke:#2563eb,color:#153145,stroke-width:2px;
    classDef positive fill:#eefbf3,stroke:#16a34a,color:#173622;
    classDef anchor fill:#f4f0ff,stroke:#7c3aed,color:#47207f;
    classDef action fill:#fff4da,stroke:#d97706,color:#6b3410;
    class caller page;
    class cli,api,request,artifact,replay positive;
    class schema anchor;
    class consumer action;
```

## Read These First

- open [API Surface](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/api-surface/) first when the contract question begins with a caller-visible schema or HTTP surface
- open [Data Contracts](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/data-contracts/) when the dispute is about retrieval payloads or replay-visible record shape
- open [Compatibility Commitments](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/compatibility-commitments/) when search-surface changes may break downstream expectations

## Contract Risk

The main contract risk here is treating retrieval behavior as backend detail while callers quietly harden dependencies against it.

## First Proof Check

- `packages/bijux-canon-index/src/bijux_canon_index/interfaces` for CLI, schema, and error surfaces
- `packages/bijux-canon-index/src/bijux_canon_index/api/v1` for HTTP routes and runtime app boundaries
- `apis/bijux-canon-index/v1/schema.yaml` for tracked schema visibility
- `packages/bijux-canon-index/tests` for replay, provenance, and compatibility evidence


## Pages In This Section

- [CLI Surface](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/cli-surface/)
- [API Surface](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/api-surface/)
- [Configuration Surface](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/configuration-surface/)
- [Data Contracts](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/data-contracts/)
- [Artifact Contracts](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/artifact-contracts/)
- [Entrypoints and Examples](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/entrypoints-and-examples/)
- [Operator Workflows](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/operator-workflows/)
- [Public Imports](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/public-imports/)
- [Compatibility Commitments](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/compatibility-commitments/)

## Leave This Section When

- leave for [Foundation](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/) when the contract dispute is really a package-boundary dispute
- leave for [Architecture](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/) when a surface question reveals structural drift underneath it
- leave for [Operations](https://bijux.io/bijux-canon/03-bijux-canon-index/operations/) or [Quality](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/) when the boundary is clear and the question becomes execution or proof

## Bottom Line

A surface is not a real contract until the docs, code, and tests agree that it is one.
