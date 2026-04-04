---
title: Release and Versioning
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Release and Versioning

Release work for `bijux-canon-reason` depends on package metadata, tracked release notes, and
the repository's commit conventions.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-reason"] --> section["Operations"]
    section --> page["Release and Versioning"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Release Anchors

- README.md
- CHANGELOG.md
- pyproject.toml

## Versioning Anchors

- version file: `packages/bijux-canon-reason/src/bijux_canon_reason/_version.py`
- tag pattern is configured in `packages/bijux-canon-reason/pyproject.toml`

## Purpose

This page ties package-local release mechanics to the wider repository release model.

## Stability

Keep it aligned with the package metadata and current versioning configuration.
