---
title: Known Limitations
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Known Limitations

Known limitations keep `bijux-canon-ingest` credible by naming what it does not promise. Trust improves when limits are explicit enough that readers do not have to discover them the hard way.

## What To Check

- name the limits that still affect prepared ingest behavior
- separate honest limits from temporary bugs or one-off breakages
- treat omitted limitations as quality debt because they mislead callers about trust boundaries

## First Proof Check

- `tests` and package-local validation surfaces for executable evidence
- caller-facing docs, limits, and risks for the trust story readers actually receive
- release notes and change records when the work alters what others may safely assume

## Bottom Line

If `bijux-canon-ingest` cannot explain why `prepared ingest behavior` should be trusted after a change, the quality work is still incomplete.
