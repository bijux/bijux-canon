---
title: Definition of Done
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Definition of Done

A change in `bijux-canon-reason` is done only when `reasoning and verification behavior` is implemented, explained, and defended together. Local success without package-level trust is not done.

## What To Check

- require code, docs, and proof to agree on the new behavior
- treat unclear release or compatibility impact as unfinished work when callers are affected
- reject “done” that depends on a reviewer inferring the missing proof story alone

## First Proof Check

- `tests` and package-local validation surfaces for executable evidence
- caller-facing docs, limits, and risks for the trust story readers actually receive
- release notes and change records when the work alters what others may safely assume

## Bottom Line

If `bijux-canon-reason` cannot explain why `reasoning and verification behavior` should be trusted after a change, the quality work is still incomplete.
