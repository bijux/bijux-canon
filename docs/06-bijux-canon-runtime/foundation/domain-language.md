---
title: Domain Language
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Domain Language

The language around `bijux-canon-runtime` should make authority explicit instead of calling it just execution, storage, or post-processing. Stable runtime nouns keep policy visible.

## Prefer These Terms

- say `acceptance`, `replay`, `persistence`, and `run authority` for runtime-owned behavior
- name artifacts by the governed run state they represent
- use `governed run` when the package is deciding whether work counts

## Avoid These Terms

- avoid using lower-package semantic terms when the issue is final authority
- avoid calling persistence alone “runtime” when acceptance policy is also in play
- avoid vague labels like `execution glue` or `final stage`

## Bottom Line

If the vocabulary makes package ownership harder to see, the vocabulary is wrong even if the sentence sounds smooth.
