---
title: Operating Guidelines
audience: mixed
type: guide
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Operating Guidelines

Changes in `bijux-canon-dev` should be especially careful because they can
affect multiple packages at once.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Maintainer Handbook"]
    section --> page["Operating Guidelines"]
    dest1["quality gates"]
    dest2["schema governance"]
    dest3["release support"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Guidelines

- prefer checks that are reviewable and testable over opaque shell glue
- keep repository automation explicit about which packages it touches
- document maintainer-only behavior in this section rather than in user-facing package pages

## Purpose

This page records the expected maintenance posture for the package.

## Stability

Update these guidelines only when the repository operating model genuinely changes.
