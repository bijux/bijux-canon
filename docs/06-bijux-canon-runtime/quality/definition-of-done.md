---
title: Definition of Done
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Definition of Done

A change in `bijux-canon-runtime` is done only when `governed run behavior` is implemented, explained, and defended together. Local success without package-level trust is not done.

## What To Check

- require code, docs, and proof to agree on the new behavior
- treat unclear release or compatibility impact as unfinished work when callers are affected
- reject “done” that depends on a reviewer inferring the missing proof story alone

## First Proof Check

- `tests` and package-local validation surfaces for executable evidence
- caller-facing docs, limits, and risks for the trust story readers actually receive
- release notes and change records when the work alters what others may safely assume

## Bottom Line

If `bijux-canon-runtime` cannot explain why `governed run behavior` should be trusted after a change, the quality work is still incomplete.
