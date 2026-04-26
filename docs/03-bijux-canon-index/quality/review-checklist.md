---
title: Review Checklist
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Review Checklist

The review checklist for `bijux-canon-index` should keep review fast without letting it become shallow. The point is to catch trust failures around retrieval and replay behavior before they ship.

## What To Check

- check whether the package boundary, contract, and proof story still agree
- confirm that code, docs, and tests moved together when behavior changed
- treat unclear filenames, symbols, or release notes as quality issues, not cosmetic ones

## First Proof Check

- `tests` and package-local validation surfaces for executable evidence
- caller-facing docs, limits, and risks for the trust story readers actually receive
- release notes and change records when the work alters what others may safely assume

## Bottom Line

If `bijux-canon-index` cannot explain why `retrieval and replay behavior` should be trusted after a change, the quality work is still incomplete.
