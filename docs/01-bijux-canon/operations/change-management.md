---
title: Change Management
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-09
---

# Change Management

The repository makes change easier to reason about, not easier to hide.

Change management here means keeping cross-package work understandable over
time. That includes how diffs are split, how release-facing effects are made
visible, and how documentation, proof, and implementation are kept in the same
story instead of being updated on separate timelines.

## Expectations

- split repository-wide work into reviewable batches with durable commit intent
- update the relevant handbook pages in the same change series as the behavior
- keep file and directory names descriptive enough that later readers do not
  need private project history to decode them
- use redirects or explicit metadata updates when documentation paths move

## What Good Looks Like

- a maintainer can read the history and understand why each batch exists
- later cleanup work is reduced because the original change closed the
  documentation and proof loop at the same time
- renamed pages or sections have an explicit continuity plan instead of silent
  breakage

## Why It Matters

Most repository rework debt comes from changes that “worked” but were never made
fully legible. Good change management is the discipline that prevents that debt
from accumulating again.

## Open This Page When

- you are planning a cross-package change series and need the repository
  discipline for splitting it
- you are reviewing history and want to understand what makes a batch durable
  instead of merely convenient
- you need the root expectation for keeping docs, proof, and implementation in
  one story

## Decision Rule

Split shared work into reviewable batches with a visible reason for each one.
If a change only makes sense when private memory fills the gaps, it is not yet
packaged well enough for repository history.

