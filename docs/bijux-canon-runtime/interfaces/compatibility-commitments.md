---
title: Compatibility Commitments
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Compatibility Commitments

Compatibility in `bijux-canon-runtime` should be explicit: stable commands, tracked schemas,
durable artifacts, and release notes that explain intentional breakage.

Read the interfaces pages for `bijux-canon-runtime` as the bridge between implementation and caller expectations: they should make public surfaces legible before a downstream dependency is formed.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-runtime"] --> section["Interfaces"]
    section --> page["Compatibility Commitments"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Compatibility Commitments"]
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
    focus3_1["Interfaces"]
    focus3 --> focus3_1
    focus3_2["tests/unit for api, contracts, core, interfaces, model, and runtime"]
    focus3 --> focus3_2
```

## Compatibility Anchors

- README.md
- CHANGELOG.md
- pyproject.toml

## Review Rule

Breaking changes must be visible in code, docs, and validation together.

## Concrete Anchors

- CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py
- HTTP app in src/bijux_canon_runtime/api/v1
- schema files in apis/bijux-canon-runtime/v1
- apis/bijux-canon-runtime/v1/schema.yaml

## Use This Page When

- you need the public command, API, import, or artifact surface
- you are checking whether a caller can rely on a given shape or entrypoint
- you need the contract-facing side of the package before using it

## Decision Rule

Use `Compatibility Commitments` to decide whether a caller-facing surface is explicit enough to be depended on. If the surface cannot be tied back to concrete code, schemas, artifacts, and tests, it should be treated as unstable until that evidence exists.

## Next Checks

- move to operations when the caller-facing question becomes procedural or environmental
- move to quality when compatibility or evidence of protection becomes the real issue
- move back to architecture when a public-surface question reveals a deeper structural drift

## Update This Page When

- commands, schemas, API modules, imports, or artifacts change in a caller-visible way
- compatibility expectations change or a new contract surface appears
- examples or entrypoints stop matching the actual package boundary

## What This Page Answers

- which public or operator-facing surfaces bijux-canon-runtime exposes
- which artifacts and schemas act like contracts
- what compatibility pressure this surface creates

## Reviewer Lens

- compare commands, API files, imports, and artifacts against the documented surface
- check whether schema or artifact changes need compatibility review
- confirm that operator-facing examples still point at real entrypoints

## Honesty Boundary

This page can identify the intended public surfaces of bijux-canon-runtime, but real compatibility still depends on code, schemas, artifacts, and tests staying aligned.

## Purpose

This page describes what should trigger compatibility review for the package.

## Stability

Keep it aligned with the package's actual public surfaces and release process.

## What Good Looks Like

- `Compatibility Commitments` leaves a caller knowing which surfaces are explicit enough to trust
- the contract discussion ties together commands, schemas, artifacts, and tests instead of treating them separately
- compatibility review becomes a visible step rather than an afterthought

## Failure Signals

- `Compatibility Commitments` names surfaces that cannot be matched to real code, schemas, or artifacts
- callers have to infer stability from examples instead of from explicit contract evidence
- compatibility review starts after change has already landed instead of before

## Tradeoffs To Hold

- prefer a smaller explicit contract over a wider surface whose stability has to be guessed
- prefer paying compatibility-review cost up front over discovering caller breakage after release
- prefer contract evidence that is slightly heavier to maintain over allowing `bijux-canon-runtime` surfaces to drift silently

## Cross Implications

- changes here shape what downstream packages and operators can safely assume about `bijux-canon-runtime`
- operations and quality pages become stale quickly if contract surfaces move silently
- architectural seams need review whenever a new public surface appears for convenience

## Approval Questions

- does `Compatibility Commitments` name only caller-facing surfaces that have explicit contract evidence
- would a downstream consumer understand compatibility expectations before depending on the surface
- are code, schemas, artifacts, examples, and tests still telling the same contract story

## Evidence Checklist

- inspect the implemented interface modules under `packages/bijux-canon-runtime/src/bijux_canon_runtime`
- review `apis/bijux-canon-runtime/v1/schema.yaml` as tracked contract evidence
- run through `packages/bijux-canon-runtime/tests` or equivalent proofs that protect the surface

## Anti-Patterns

- treating convenience surfaces as if they were deliberate contracts
- changing schemas or artifacts without a caller-facing compatibility discussion
- using examples to imply stability that code and tests do not actually promise

## Escalate When

- a supposedly local change alters a caller-visible schema, artifact, import, or command contract
- compatibility risk extends beyond one implementation file
- operators or downstream packages would need to relearn the surface after the change

## Core Claim

The interface claim of `bijux-canon-runtime` is that commands, APIs, imports, schemas, and artifacts form a reviewable contract rather than an implied one.

## Why It Matters

If the interface pages for `bijux-canon-runtime` are weak, callers cannot tell which commands, schemas, or artifacts are stable enough to depend on, and compatibility review arrives too late.

## If It Drifts

- callers depend on surfaces that are less stable than the docs imply
- schema and artifact changes stop receiving the compatibility review they need
- operator examples begin pointing at stale or misleading entrypaths

## Representative Scenario

An operator or downstream caller wants to depend on a `bijux-canon-runtime` surface and needs to know which command, API, schema, import, or artifact is stable enough to treat as a contract.

## Source Of Truth Order

- `packages/bijux-canon-runtime/src/bijux_canon_runtime` for the implemented boundary
- `apis/bijux-canon-runtime/v1/schema.yaml` as tracked contract evidence
- `packages/bijux-canon-runtime/tests` for compatibility and behavior proof

## Common Misreadings

- that every visible package surface is equally stable
- that one schema or example is the whole compatibility story
- that interface docs override package code, artifacts, or tests when they disagree
