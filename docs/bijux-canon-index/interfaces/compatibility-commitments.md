---
title: Compatibility Commitments
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Compatibility Commitments

Compatibility in `bijux-canon-index` should be explicit: stable commands, tracked schemas,
durable artifacts, and release notes that explain intentional breakage.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-index"] --> section["Interfaces"]
    section --> page["Compatibility Commitments"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Compatibility Anchors

- README.md
- CHANGELOG.md
- pyproject.toml

## Review Rule

Breaking changes must be visible in code, docs, and validation together.

## Purpose

This page describes what should trigger compatibility review for the package.

## Stability

Keep it aligned with the package's actual public surfaces and release process.
