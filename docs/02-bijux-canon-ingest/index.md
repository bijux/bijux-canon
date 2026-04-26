---
title: Ingest Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Ingest Handbook

`bijux-canon-ingest` owns deterministic document preparation, chunking, and
retrieval-ready shaping. Open this handbook when you need to understand how
source material becomes stable ingest output.

This package sits at the front of the canonical package family. Its job is to
turn raw source material into chunks, records, and artifacts that downstream
packages can index, reason over, and orchestrate without having to reinterpret
the ingest step from scratch.

## Open This Handbook When

- you need the package-level entrypoint for ingest docs
- you are checking ingest workflows, chunking, or retrieval preparation
- you want the shortest route into the owned ingest documentation
- you need to decide whether a concern belongs in ingest or in a downstream
  package

## What This Package Owns

- deterministic preparation of source material before retrieval
- chunking, record shaping, and ingest-side artifact generation
- ingest workflows that downstream packages can rely on as stable input

## What This Package Does Not Own

- vector-store execution and replayable retrieval behavior
- reasoning, verification, or claim-production semantics
- cross-package runtime acceptance, persistence, and operator governance

## Choose A Section

- open [Foundation](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/) when the real question is why ingest
  exists, where the boundary stops, or which language should stay stable
- open [Architecture](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/) when you need the module map,
  dependency direction, or execution flow
- open [Interfaces](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/) when the question is about commands,
  schemas, artifacts, or import surfaces
- open [Operations](https://bijux.io/bijux-canon/02-bijux-canon-ingest/operations/) when you need setup, local workflow,
  diagnostics, or release guidance
- open [Quality](https://bijux.io/bijux-canon/02-bijux-canon-ingest/quality/) when you need proof expectations, risk
  posture, or a review standard

## Pages In This Handbook

- [Foundation](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/)
- [Architecture](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/)
- [Interfaces](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/)
- [Operations](https://bijux.io/bijux-canon/02-bijux-canon-ingest/operations/)
- [Quality](https://bijux.io/bijux-canon/02-bijux-canon-ingest/quality/)

## Why Start Here

Open this handbook when the important question is how material becomes
ingest-ready in a deterministic way. If the question starts after chunked or
prepared artifacts already exist, one of the downstream package handbooks is
probably the better starting point.
