---
title: Architecture Risks
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Architecture Risks

Architecture risks in `bijux-canon-index` are the ways the code can stop defending retrieval execution, replay, and provenance. The point is to surface those risks early enough that reviewers can challenge them before they harden.

## What To Check

- rank the risks by how much they blur package ownership or weaken proof quality
- watch for risk patterns that pull ingest, reason, and runtime concerns into `bijux-canon-index`
- treat unexplained complexity as a risk, even when tests are still green

## First Proof Check

- `src/bijux_canon_index` and `apis` for the structural ownership boundary
- `tests` for replay and provenance evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-index` needs hidden structure to defend retrieval execution, replay, and provenance, the architecture is already too opaque.
