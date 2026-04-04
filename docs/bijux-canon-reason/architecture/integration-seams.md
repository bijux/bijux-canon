---
title: Integration Seams
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Integration Seams

Integration seams are the points where `bijux-canon-reason` meets configuration, APIs,
operators, or neighboring packages.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-reason"] --> section["Architecture"]
    section --> page["Integration Seams"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Integration Seams"]
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
    focus3_1["Architecture"]
    focus3 --> focus3_1
    focus3_2["tests/unit for planning, reasoning, execution, verification, and interfaces"]
    focus3 --> focus3_2
```

## Integration Surfaces

- CLI app in src/bijux_canon_reason/interfaces/cli
- HTTP app in src/bijux_canon_reason/api/v1
- schema files in apis/bijux-canon-reason/v1

## Adjacent Systems

- consumes evidence prepared by ingest and retrieval provided by index
- relies on runtime when a run must be accepted, stored, or replayed under policy

## Use This Page When

- you are tracing internal structure or execution flow
- you need to understand where modules fit before refactoring
- you are reviewing architectural drift instead of one local bug

## What This Page Answers

- how bijux-canon-reason is structured internally
- which modules control the main execution path
- where architectural drift would become visible first

## Reviewer Lens

- trace the claimed execution path through the listed modules
- look for dependency direction that now contradicts the documented seam
- verify that architectural risks still match the current code structure

## Honesty Boundary

This page describes the current structural model of bijux-canon-reason, but it does not by itself prove that every import or runtime path still obeys that model.

## Purpose

This page explains where to look when integration behavior changes.

## Stability

Keep it aligned with real boundary modules and schema files.
