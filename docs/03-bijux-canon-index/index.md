---
title: Index Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Index Handbook

`bijux-canon-index` owns vector execution, provenance-aware retrieval, and
replayable index behavior. Use this handbook when you need to understand
vector-store behavior, retrieval execution, or index-side public contracts.

This package turns ingest-ready artifacts into searchable, replayable retrieval
surfaces. It is where embedding execution, index persistence, and retrieval
behavior need to become explicit enough for downstream reasoning and runtime
flows to trust.

```mermaid
flowchart LR
    ingest["ingest-ready chunks and records"]
    index["bijux-canon-index<br/>embed, store, retrieve, replay"]
    reason["bijux-canon-reason<br/>claims and verification"]
    runtime["bijux-canon-runtime<br/>run acceptance and persistence"]
    reader["reader question<br/>how does retrieval actually work?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class ingest,page index;
    class reason,runtime,reader positive;
    ingest --> index --> reason --> runtime
    index --> reader
```

## Use This Handbook When

- you need the package-level entrypoint for index docs
- you are checking vector execution, retrieval, or replay-aware index behavior
- you want the shortest route into the owned index documentation
- you need to separate index-side concerns from ingest preparation or reasoning
  semantics

## What This Package Owns

- vector creation and execution behavior tied to canonical ingest output
- provenance-aware retrieval and replayable index behavior
- index-facing contracts that downstream packages depend on during retrieval

## What This Package Does Not Own

- source preparation and chunk shaping before indexing
- reasoning semantics, verification policy, or claim interpretation
- top-level runtime governance above retrieval execution

## Choose A Section

- use [Foundation](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/) when you need the package boundary,
  vocabulary, or ownership story
- use [Architecture](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/) when the question is about module
  layout, dependency direction, or replay flow
- use [Interfaces](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/) when you need commands, schemas,
  artifacts, or import surfaces
- use [Operations](https://bijux.io/bijux-canon/03-bijux-canon-index/operations/) when you need setup, diagnostics,
  local workflow, or release guidance
- use [Quality](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/) when you need proof expectations, risk
  posture, or review standards

## Pages In This Handbook

- [Foundation](https://bijux.io/bijux-canon/03-bijux-canon-index/foundation/)
- [Architecture](https://bijux.io/bijux-canon/03-bijux-canon-index/architecture/)
- [Interfaces](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/)
- [Operations](https://bijux.io/bijux-canon/03-bijux-canon-index/operations/)
- [Quality](https://bijux.io/bijux-canon/03-bijux-canon-index/quality/)

## Why Start Here

Use this handbook when the hard question is about retrieval behavior itself:
what gets embedded, how replay works, and which index contracts downstream
packages are allowed to trust.
