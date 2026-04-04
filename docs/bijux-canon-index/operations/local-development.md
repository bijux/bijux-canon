---
title: Local Development
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Local Development

Local development should happen inside `packages/bijux-canon-index` with tests and docs updated
in the same change series as the code.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-index"] --> section["Operations"]
    section --> page["Local Development"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Local Development"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["vector execution semantics and backend orchestration"]
    focus1 --> focus1_1
    focus1_2["provenance-aware result artifacts and replay-oriented comparison"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_index/domain"]
    focus2 --> focus2_1
    focus2_2["vector execution result collections"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Operations"]
    focus3 --> focus3_1
    focus3_2["tests/unit for API, application, contracts, domain, infra, and tooling"]
    focus3 --> focus3_2
```

## Development Anchors

- tests/unit for API, application, contracts, domain, infra, and tooling
- tests/e2e for CLI workflows, API smoke, determinism gates, and provenance gates
- tests/conformance and tests/compat_v01 for compatibility behavior
- tests/stress and tests/scenarios for operational pressure checks

## Concrete Anchors

- `packages/bijux-canon-index/pyproject.toml` for package metadata
- `packages/bijux-canon-index/README.md` for local package framing
- `packages/bijux-canon-index/tests` for executable operational backstops

## Use This Page When

- you are installing, running, diagnosing, or releasing the package
- you need operational anchors rather than conceptual framing
- you are responding to package behavior in a local or CI environment

## Next Checks

- move to interfaces when the operational path depends on a specific surface contract
- move to quality when the question becomes whether the workflow is sufficiently proven
- move back to architecture when operational complexity suggests a structural problem

## What This Page Answers

- how bijux-canon-index is installed, run, diagnosed, and released
- which files or tests matter during package operation
- where an operator should look when behavior changes

## Reviewer Lens

- verify that setup, workflow, and release references still match package metadata
- check that operational docs point at current diagnostics and validation paths
- confirm that release-facing claims match the package's actual versioning files

## Honesty Boundary

This page explains how bijux-canon-index is expected to be operated, but it does not replace package metadata, runtime behavior, or validation runs in a real environment.

## Purpose

This page records the package-local development posture.

## Stability

Keep it aligned with the actual test layout and maintenance workflow.

## Core Claim

The operational claim of `bijux-canon-index` is that install, run, diagnose, and release paths can be repeated from explicit package assets instead of oral history.

## Why It Matters

If the operations pages for `bijux-canon-index` are weak, maintainers end up relearning install, diagnose, and release behavior from trial and error instead of from checked-in package truth.

## If It Drifts

- maintainers relearn package operation by trial and error
- release and setup steps quietly diverge from the checked-in package metadata
- diagnostic workflows become harder to repeat under incident pressure

## Representative Scenario

A maintainer is trying to run, diagnose, or release `bijux-canon-index` under time pressure and needs an explicit path that starts from checked-in metadata and lands in repeatable validation.

## Source Of Truth Order

- `packages/bijux-canon-index/pyproject.toml` for install and release metadata
- `packages/bijux-canon-index/README.md` and package tests for operator truth
- this page for the repeatable workflow narrative that should match those assets

## Common Misreadings

- that the shortest operator path is the same thing as the most authoritative source
- that setup or release behavior can be inferred without checking package metadata
- that passing one local run proves the operational contract is fully intact
