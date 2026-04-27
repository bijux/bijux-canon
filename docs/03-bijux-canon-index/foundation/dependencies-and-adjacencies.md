---
title: Dependencies and Adjacencies
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Dependencies and Adjacencies

Dependency and adjacency pressure in `bijux-canon-index` matters because backends, plugins, and replay features can make retrieval semantics look accidental. Reviewers need the semantics named explicitly so they stay visible.

## Library Pressure

- vector-store and embedding dependencies support search behavior but do not define its public meaning by themselves
- schema and interface helpers matter because search contracts become caller obligations quickly
- library choice should never be the only explanation for why retrieval behaves the way it does

## Neighbor Pressure

- `bijux-canon-ingest` feeds prepared input into index behavior
- `bijux-canon-reason` consumes retrieved evidence without owning how search happened
- `bijux-canon-runtime` governs runs that include retrieval without redefining retrieval semantics

## Bottom Line

Dependencies matter, but they should never be allowed to silently redefine package ownership.
