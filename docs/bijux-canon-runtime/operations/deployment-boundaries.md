---
title: Deployment Boundaries
audience: mixed
type: guide
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Deployment Boundaries

Deployment for `bijux-canon-runtime` should respect the package boundary instead of assuming the full repository is always present.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-runtime"] --> section["Operations"]
    section --> page["Deployment Boundaries"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Deployment Boundaries"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["flow execution authority"]
    focus1 --> focus1_1
    focus1_2["replay and acceptability semantics"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_runtime/model"]
    focus2 --> focus2_1
    focus2_2["execution store records"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Operations"]
    focus3 --> focus3_1
    focus3_2["tests/unit for api, contracts, core, interfaces, model, and runtime"]
    focus3 --> focus3_2
```

## Boundary Facts

- package root: `packages/bijux-canon-runtime`
- public metadata: `packages/bijux-canon-runtime/pyproject.toml`
- release notes: `packages/bijux-canon-runtime/CHANGELOG.md` when present

## Use This Page When

- you are installing, running, diagnosing, or releasing the package
- you need operational anchors rather than conceptual framing
- you are responding to package behavior in a local or CI environment

## What This Page Answers

- how bijux-canon-runtime is installed, run, diagnosed, and released
- which files or tests matter during package operation
- where an operator should look when behavior changes

## Reviewer Lens

- verify that setup, workflow, and release references still match package metadata
- check that operational docs point at current diagnostics and validation paths
- confirm that release-facing claims match the package's actual versioning files

## Honesty Boundary

This page explains how bijux-canon-runtime is expected to be operated, but it does not replace package metadata, runtime behavior, or validation runs in a real environment.

## Purpose

This page reminds maintainers that packages are publishable units, not just folders in one repo.

## Stability

Keep it aligned with the package's actual distributable surface.
