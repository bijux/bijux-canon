---
title: Dependencies and Adjacencies
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Dependencies and Adjacencies

Dependency and adjacency pressure in `bijux-canon-reason` matters because meaning is easy to blur across prompts, retrieval output, and workflow code. Reviewers need the seams named explicitly so they stay visible.

## Library Pressure

- reasoning helpers and model-facing dependencies support the package but do not define its policy by themselves
- artifact and schema helpers matter because reasoning outputs become inputs to later layers
- library choice is never enough reason to move reasoning authority across package boundaries

## Neighbor Pressure

- `bijux-canon-index` supplies evidence without owning claim meaning
- `bijux-canon-agent` consumes reasoning outputs without redefining their internal logic
- `bijux-canon-runtime` governs whole runs without replacing reasoning policy

## Bottom Line

Dependencies matter, but they should never be allowed to silently redefine package ownership.
