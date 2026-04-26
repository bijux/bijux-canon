---
title: Artifact Governance
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Artifact Governance

Generated output is useful only when its status is obvious.

The repository needs a simple distinction between source, tracked reference
artifacts, and disposable validation output. Without that distinction,
reviewers waste time guessing whether a generated file is authoritative,
incidental, or stale.

## Artifact Classes

- tracked reference artifacts under `apis/` when schema review depends on them
- tracked release-facing or repository-facing evidence when a checked history
  is part of the review surface
- generated local or CI output under `artifacts/` when the output supports
  validation rather than source

## First Proof Checks

- `apis/` when the artifact is part of a public contract review
- `artifacts/` when the output exists only to prove or inspect a run
- package release files when the artifact is part of published package evidence

## Common Failure Mode

The easiest artifact mistake is letting transient output look canonical because
it sits near source or because a workflow generated it once. If review would not
compare historical versions of the file on purpose, it probably does not belong
in a tracked source surface.

## Bottom Line

Keep tracked artifacts only when review depends on a stable checked history.
Send transient run products to `artifacts/` so source stays legible.
