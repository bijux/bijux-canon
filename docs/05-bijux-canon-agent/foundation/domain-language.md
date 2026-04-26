---
title: Domain Language
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Domain Language

The language around `bijux-canon-agent` should make orchestration visible instead of calling it intelligence, magic, or just “the flow.” Stable orchestration nouns reduce confusion with reasoning and runtime.

## Prefer These Terms

- say `orchestration`, `workflow`, `role`, and `trace` for agent-owned behavior
- name outputs by the step or coordination purpose they serve
- use `role handoff` and `workflow progression` when describing agent-local sequencing

## Avoid These Terms

- avoid calling claim logic or retrieval behavior “agent behavior” when orchestration is only consuming it
- avoid runtime terms such as `acceptance` or `authority` for local workflow control
- avoid vague labels like `agent magic` or `smart chain`

## Bottom Line

If the vocabulary makes package ownership harder to see, the vocabulary is wrong even if the sentence sounds smooth.
