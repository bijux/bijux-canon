---
title: Failure Recovery
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Failure Recovery

Failure recovery starts with knowing which artifacts, interfaces, and tests expose the problem.

This page should help a maintainer stabilize the situation before they try to
improve it. The first question is not always how to fix the bug; it is how to
locate the right evidence quickly.

Treat the operations pages for `bijux-canon-runtime` as the package's explicit operating memory. They should make common tasks repeatable without relearning the workflow from logs or oral history.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-runtime"] --> section["Operations"]
    section --> page["Failure Recovery"]
    dest1["repeat workflows"]
    dest2["find diagnostics"]
    dest3["release safely"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Failure Recovery"]
    focus1["Workflow anchors"]
    page --> focus1
    focus1_1["packages/bijux-canon-runtime/pyproject.toml"]
    focus1 --> focus1_1
    focus1_2["CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py"]
    focus1 --> focus1_2
    focus2["Operational evidence"]
    page --> focus2
    focus2_1["tests/unit for api, contracts, core, interfaces, model, and runtime"]
    focus2 --> focus2_1
    focus2_2["execution store records"]
    focus2 --> focus2_2
    focus3["Release pressure"]
    page --> focus3
    focus3_1["README.md"]
    focus3 --> focus3_1
    focus3_2["Failure Recovery"]
    focus3 --> focus3_2
```

## Recovery Anchors

- interface surfaces: CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py, HTTP app in src/bijux_canon_runtime/api/v1, schema files in apis/bijux-canon-runtime/v1
- artifacts to inspect: execution store records, replay decision artifacts, non-determinism policy evaluations
- tests to run: tests/unit for api, contracts, core, interfaces, model, and runtime, tests/e2e for governed flow behavior

## Concrete Anchors

- `packages/bijux-canon-runtime/pyproject.toml` for package metadata
- `packages/bijux-canon-runtime/README.md` for local package framing
- `packages/bijux-canon-runtime/tests` for executable operational backstops

## Use This Page When

- you are installing, running, diagnosing, or releasing the package
- you need repeatable operational anchors rather than architectural framing
- you are responding to package behavior in local work, CI, or incident pressure

## Decision Rule

Use `Failure Recovery` to decide whether a maintainer can repeat the package workflow from checked-in assets instead of memory. If a step works only because someone already knows the trick, the workflow is not documented clearly enough yet.

## What This Page Answers

- how `bijux-canon-runtime` is installed, run, diagnosed, and released in practice
- which checked-in files and tests anchor the operational story
- where a maintainer should look first when the package behaves differently

## Reviewer Lens

- verify that setup, workflow, and release statements still match package metadata and current commands
- check that operational guidance still points at real diagnostics and validation paths
- confirm that maintainer advice still works under current local and CI expectations

## Honesty Boundary

This page explains how `bijux-canon-runtime` is expected to be operated, but it does not replace package metadata, actual runtime behavior, or validation in a real environment. A workflow is only trustworthy if a maintainer can still repeat it from the checked-in assets named here.

## Next Checks

- move to interfaces when the operational path depends on a specific surface contract
- move to quality when the question becomes whether the workflow is sufficiently proven
- move back to architecture when operational complexity suggests a structural problem

## Purpose

This page gives maintainers a durable frame for triaging package failures.

## Stability

Keep it aligned with the package entrypoints and diagnostic outputs.
