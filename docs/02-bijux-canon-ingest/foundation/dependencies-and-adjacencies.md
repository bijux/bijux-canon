---
title: Dependencies and Adjacencies
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Dependencies and Adjacencies

Dependency and adjacency pressure in `bijux-canon-ingest` matters because convenience can easily push foreign responsibilities into source preparation. Reviewers need the pressure named explicitly so they can resist it.

## Library Pressure

- `pydantic`, `msgpack`, and `numpy` shape local data handling and serialization
- `fastapi`, `uvicorn`, and configuration helpers support package-local interfaces
- none of those libraries change the fact that ingest stops before retrieval semantics and runtime authority

## Neighbor Pressure

- `bijux-canon-index` depends on ingest output being stable enough to search
- `bijux-canon-reason` depends on later layers receiving coherent prepared evidence
- `bijux-canon-runtime` governs runs that include ingest without giving ingest run authority

## Bottom Line

Dependencies matter, but they should never be allowed to silently redefine package ownership.
