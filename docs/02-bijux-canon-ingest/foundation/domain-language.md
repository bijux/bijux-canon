---
title: Domain Language
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Domain Language

The language around `bijux-canon-ingest` should keep source preparation distinct from retrieval, reasoning, and runtime authority. When names blur those seams, reviewers spend time arguing about nouns instead of behavior.

## Prefer These Terms

- say `prepared input`, `chunking`, and `source normalization` for ingest-owned work
- say `handoff` when ingest output becomes downstream input
- name artifacts by the stable record they contain, not by an internal step nickname

## Avoid These Terms

- avoid calling retrieval behavior “ingest” just because it consumes ingest output
- avoid runtime terms such as `replay authority` or `acceptance` for local preparation behavior
- avoid vague labels such as `pipeline magic`, `smart preprocessing`, or `just cleanup`

## Bottom Line

If the vocabulary makes package ownership harder to see, the vocabulary is wrong even if the sentence sounds smooth.
