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

## Read These First

- open [API Surface](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/api-surface/) first when the contract question begins with a caller-visible schema or HTTP surface
- open [Data Contracts](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/data-contracts/) when the dispute is about retrieval payloads or replay-visible record shape
- open [Compatibility Commitments](https://bijux.io/bijux-canon/03-bijux-canon-index/interfaces/compatibility-commitments/) when search-surface changes may break downstream expectations

## Contract Risk

The main contract risk here is treating retrieval behavior as backend detail while callers quietly harden dependencies against it.

## First Proof Check

- `src/bijux_canon_index/interfaces` and `apis` for named caller-facing surfaces
- tracked schemas and examples for contract visibility
- `tests` for replay, provenance, and compatibility evidence


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
