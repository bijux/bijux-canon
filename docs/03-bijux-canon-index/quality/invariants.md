---
title: Invariants
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Invariants

Invariants are the promises `bijux-canon-index` should lose only through a deliberate design decision. If a change weakens an invariant without naming it, trust has already eroded.

## What To Check

- name the truths that must survive ordinary changes to retrieval and replay behavior
- tie each invariant to the evidence that is supposed to protect it
- treat invariant drift as a design event rather than a routine edit

## First Proof Check

- `tests` and package-local validation surfaces for executable evidence
- caller-facing docs, limits, and risks for the trust story readers actually receive
- release notes and change records when the work alters what others may safely assume

## Bottom Line

If `bijux-canon-index` cannot explain why `retrieval and replay behavior` should be trusted after a change, the quality work is still incomplete.
