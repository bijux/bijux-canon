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

```mermaid
flowchart TD
    page["Release and Versioning"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["reasoning plans, claims, and evidence-aware reasoning models"]
    focus1 --> focus1_1
    focus1_2["execution of reasoning steps and local tool dispatch"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_reason/planning"]
    focus2 --> focus2_1
    focus2_2["reasoning traces and replay diffs"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Operations"]
    focus3 --> focus3_1
    focus3_2["tests/unit for planning, reasoning, execution, verification, and interfaces"]
    focus3 --> focus3_2
```

## Release Anchors

- README.md
- CHANGELOG.md
- pyproject.toml

## Versioning Anchors

- version file: `packages/bijux-canon-reason/src/bijux_canon_reason/_version.py`
- tag pattern is configured in `packages/bijux-canon-reason/pyproject.toml`

## What This Page Answers

- how bijux-canon-reason is installed, run, diagnosed, and released
- which files or tests matter during package operation
- where an operator should look when behavior changes

## Purpose

This page ties package-local release mechanics to the wider repository release model.

## Stability

Keep it aligned with the package metadata and current versioning configuration.
