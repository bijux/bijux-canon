---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Interfaces

Open this section when the question is contractual: which ingest commands, schemas, records, artifacts, and imports are safe for another tool or package to rely on.

## Contract Surface

Ingest exposes more than one kind of interface. Operators reach it through CLI
and HTTP surfaces, package callers rely on imports and serialized records, and
downstream packages consume artifacts that must remain stable enough to review.
This section should name those promises before a reader has to inspect code.

```mermaid
flowchart LR
    caller["caller or operator"]
    cli["CLI surface<br/>commands and options"]
    api["API surface<br/>HTTP models and routes"]
    config["configuration<br/>ingest, parsing, cleaning"]
    data["data contracts<br/>chunks, metadata, envelopes"]
    artifacts["artifact contracts<br/>prepared outputs"]
    downstream["downstream package<br/>index handoff"]

    caller --> cli --> data
    caller --> api --> data
    caller --> config --> data
    data --> artifacts --> downstream
    data -. schema evidence .-> schema["apis/bijux-canon-ingest/v1/schema.yaml"]

    classDef page fill:#eef6ff,stroke:#2563eb,color:#153145,stroke-width:2px;
    classDef positive fill:#eefbf3,stroke:#16a34a,color:#173622;
    classDef anchor fill:#f4f0ff,stroke:#7c3aed,color:#47207f;
    classDef action fill:#fff4da,stroke:#d97706,color:#6b3410;
    class caller page;
    class cli,api,config,data,artifacts positive;
    class schema anchor;
    class downstream action;
```

## Read These First

- open [Data Contracts](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/data-contracts/) first when the dispute is about record shape, chunk structure, or prepared payload layout
- open [CLI Surface](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/cli-surface/) when the issue begins with an operator or scripted entrypoint
- open [Compatibility Commitments](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/compatibility-commitments/) when a surface change may break downstream assumptions

## Contract Risk

The main contract risk here is letting downstream packages rely on visible ingest behavior that was never named as a real contract.

## First Proof Check

- `packages/bijux-canon-ingest/src/bijux_canon_ingest/interfaces` for CLI, HTTP, serialization, and error bridges
- `packages/bijux-canon-ingest/src/bijux_canon_ingest/config` for caller-visible ingest, parsing, and cleaning settings
- `apis/bijux-canon-ingest/v1/schema.yaml` for tracked schema evidence
- `packages/bijux-canon-ingest/tests` and examples for proof that exposed ingest behavior is intentional


## Pages In This Section

- [CLI Surface](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/cli-surface/)
- [API Surface](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/api-surface/)
- [Configuration Surface](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/configuration-surface/)
- [Data Contracts](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/data-contracts/)
- [Artifact Contracts](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/artifact-contracts/)
- [Entrypoints and Examples](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/entrypoints-and-examples/)
- [Operator Workflows](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/operator-workflows/)
- [Public Imports](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/public-imports/)
- [Compatibility Commitments](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/compatibility-commitments/)

## Leave This Section When

- leave for [Foundation](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/) when the contract dispute is really a package-boundary dispute
- leave for [Architecture](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/) when a surface question reveals structural drift underneath it
- leave for [Operations](https://bijux.io/bijux-canon/02-bijux-canon-ingest/operations/) or [Quality](https://bijux.io/bijux-canon/02-bijux-canon-ingest/quality/) when the boundary is clear and the question becomes execution or proof

## Bottom Line

A surface is not a real contract until the docs, code, and tests agree that it is one.
