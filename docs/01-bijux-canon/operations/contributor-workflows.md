---
title: Contributor Workflows
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-09
---

# Contributor Workflows

Contributors should be able to move through the repository in a repeatable
order.

The healthy path is simple: understand the owning boundary, make the change in
the owning location, update the proof that matches the change, and only then
escalate to repository-wide automation when the work genuinely crosses package
boundaries. The root should help that path feel consistent rather than magical.

## Common Workflow Shape

- start in the relevant handbook section before editing shared files
- make package-local changes in the owning package when the behavior is local
- use root automation when the work spans docs, schemas, release flow, or more
  than one package
- update the explanation and proof in the same change series

## Shared Contributor Anchors

- `CONTRIBUTING.md` for repository expectations
- `Makefile` and `makes/` for shared entrypoints
- `.github/workflows/` for repository verification and publication flow
- the handbook sections under `docs/` for durable operational memory

## Failure Signals

- a contributor has to ask which root command is “the real one” for common work
- maintainer-only workflow knowledge lives mostly in chat history or CI output
- the same cross-package procedure is being rediscovered from scratch

