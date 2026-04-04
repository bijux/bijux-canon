---
title: Compatibility Overview
audience: mixed
type: guide
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Compatibility Overview

These packages exist to reduce migration breakage, not to become the preferred
long-term entrypoints for new work.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Compatibility Handbook"]
    section --> page["Compatibility Overview"]
    dest1["legacy package names"]
    dest2["migration decisions"]
    dest3["retirement review"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Compatibility Overview"]
    focus1["Legacy surface"]
    page --> focus1
    focus1_1["distribution names"]
    focus1 --> focus1_1
    focus1_2["import names"]
    focus1 --> focus1_2
    focus2["Canonical target"]
    page --> focus2
    focus2_1["current packages"]
    focus2 --> focus2_1
    focus2_2["new work"]
    focus2 --> focus2_2
    focus3["Decision pressure"]
    page --> focus3
    focus3_1["migration"]
    focus3 --> focus3_1
    focus3_2["retirement"]
    focus3 --> focus3_2
```

## Preserved Surfaces

- legacy distribution names
- legacy Python import names
- legacy command names where they still exist

## What This Page Answers

- which legacy surface is still preserved
- when new work should move to the canonical package instead
- what evidence would justify retiring a compatibility package

## Purpose

This page gives the shortest honest description of why the compatibility packages remain.

## Stability

Keep it aligned with the actual compatibility promises that are still checked in.
