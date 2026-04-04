---
title: Local Development
audience: mixed
type: guide
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# Local Development

Local work should happen through the publishable packages plus the root
orchestration commands that keep the repository consistent.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Repository Handbook"]
    section --> page["Local Development"]
    dest1["package boundaries"]
    dest2["shared workflows"]
    dest3["reviewable decisions"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Local Development"]
    focus1["Repository intent"]
    page --> focus1
    focus1_1["scope"]
    focus1 --> focus1_1
    focus1_2["shared ownership"]
    focus1 --> focus1_2
    focus2["Review inputs"]
    page --> focus2
    focus2_1["code"]
    focus2 --> focus2_1
    focus2_2["schemas"]
    focus2 --> focus2_2
    focus2_3["automation"]
    focus2 --> focus2_3
    focus3["Review outputs"]
    page --> focus3
    focus3_1["clear decisions"]
    focus3 --> focus3_1
    focus3_2["stable docs"]
    focus3 --> focus3_2
```

## Working Rules

- make package-local changes in the owning package directory
- use root automation when the change spans packages, schemas, or docs
- keep documentation updates reviewable alongside the code that changes behavior

## Shared Inputs

- `pyproject.toml` for commitizen and workspace metadata
- `tox.ini` for root validation environments
- `Makefile` and `makes/` for common workflows

## What This Page Answers

- which repository-level decision this page clarifies
- which shared assets or workflows a reviewer should inspect
- how the repository boundary differs from package-local ownership

## Purpose

This page records the preferred development posture for the workspace without repeating package-specific setup details.

## Stability

Keep this page aligned with the root automation files that actually exist.
