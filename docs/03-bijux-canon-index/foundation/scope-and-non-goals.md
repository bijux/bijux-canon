---
title: Scope and Non-Goals
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Scope and Non-Goals

The scope of `bijux-canon-index` is to make search behavior explicit enough to defend. It is not a general home for “things that happen around retrieval.”

## In Scope

- vector execution and backend coordination tied to prepared ingest output
- replayable retrieval behavior and provenance-rich search results
- index-facing contracts that downstream reasoning and runtime flows rely on

## Non-Goals

- normalizing source material before search begins
- deciding what retrieved evidence means for a claim or verification step
- deciding whether a whole run is acceptable or durable under runtime policy

## Scope Check

If the change can only be explained by saying “search needs it somewhere,” the ownership argument is not strong enough yet.

## Bottom Line

A package boundary earns trust partly by the work it refuses to absorb. `bijux-canon-index` should stay narrow enough that its role can still be explained in one pass.
