---
title: Package Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Package Map

The package map is the clearest explanation of the product idea in this
repository. Each canonical package owns one part of a larger system, and the
handoff between them is the design.

## Responsibility Chain

| Package | Core role | What it hands forward |
| --- | --- | --- |
| `bijux-canon-ingest` | deterministic preparation of input material | normalized, retrieval-ready material |
| `bijux-canon-index` | retrieval execution and provenance-rich result handling | replayable evidence retrieval state |
| `bijux-canon-reason` | evidence-aware reasoning, claims, and verification | inspectable conclusions tied to evidence |
| `bijux-canon-agent` | role-based orchestration and trace-backed workflow control | coordinated multi-step work with explicit traces |
| `bijux-canon-runtime` | governed execution, replay, persistence, and final acceptability | accepted or replayable run outcomes |

## Common Misreads

- ingest is not the long-term owner of retrieval execution
- index is not the owner of reasoning semantics
- reason is not the owner of orchestration or final runtime authority
- agent is not the owner of package-local scientific truth
- runtime is not the place to absorb behavior merely because it sits last in the chain

## First Proof Checks

- `packages/` for the canonical boundaries themselves
- package handbook roots for the owned promises behind each name
- `Makefile`, `makes/`, and `.github/workflows/` only when the question is
  about shared enforcement rather than package behavior

## Bottom Line

Read the package family as a chain of owned responsibilities, not as taxonomy.
The map is useful only if it helps a reviewer put a change in one owner faster.
