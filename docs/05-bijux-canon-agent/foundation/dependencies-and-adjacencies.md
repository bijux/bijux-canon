---
title: Dependencies and Adjacencies
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Dependencies and Adjacencies

Dependency and adjacency pressure in `bijux-canon-agent` matters because workflow code naturally reaches into neighboring packages. Reviewers need coordination ownership named explicitly so it stays separate from the work being coordinated.

## Library Pressure

- role and workflow helpers support orchestration but do not justify owning reasoning or runtime policy
- interface and artifact helpers matter because workflow behavior becomes a caller-visible contract quickly
- library choice should never be the only reason to change the orchestration boundary

## Neighbor Pressure

- `bijux-canon-reason` supplies reasoning outputs that workflows coordinate
- `bijux-canon-runtime` governs the completed run without re-owning workflow semantics
- lower canonical packages remain responsible for the semantics of their own outputs

## Bottom Line

Dependencies matter, but they should never be allowed to silently redefine package ownership.
