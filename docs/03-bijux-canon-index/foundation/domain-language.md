---
title: Domain Language
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Domain Language

The language around `bijux-canon-index` should make retrieval behavior explicit instead of hiding it behind storage or infrastructure words. Search semantics need first-class names.

## Prefer These Terms

- say `retrieval behavior`, `replay`, and `provenance` for index-owned concerns
- name backend adapters as implementation choices rather than as the meaning of the package
- name outputs by what they let a caller inspect, compare, or replay

## Avoid These Terms

- avoid calling retrieval execution “just infrastructure”
- avoid reasoning terms such as `claim` or `verification` for index-local outputs
- avoid generic words like `search stuff` when a stable retrieval noun exists

## Bottom Line

If the vocabulary makes package ownership harder to see, the vocabulary is wrong even if the sentence sounds smooth.
