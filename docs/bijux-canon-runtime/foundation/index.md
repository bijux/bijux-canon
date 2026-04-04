---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Foundation

Start the bijux-canon-runtime handbook here when you need the package in one honest sentence: what it owns, why it exists, and where its boundary stops.

These pages establish the durable idea of `bijux-canon-runtime`. A reader should be able to skim this section and understand why the package exists, what neighboring packages should not assume about it, and which claims are worth defending during review.

Read the foundation pages for `bijux-canon-runtime` as the package's durable self-description. They should let a reader understand the package without needing to reconstruct its purpose from recent implementation history.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-runtime"] --> section["Foundation"]
    section --> page["Foundation"]
    dest1["own the right work"]
    dest2["name the boundary"]
    dest3["compare neighbors"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Foundation"]
    focus1["Owned here"]
    page --> focus1
    focus1_1["flow execution authority"]
    focus1 --> focus1_1
    focus1_2["replay and acceptability semantics"]
    focus1 --> focus1_2
    focus2["Not owned here"]
    page --> focus2
    focus2_1["agent composition policy"]
    focus2 --> focus2_1
    focus2_2["ingest and index domain ownership"]
    focus2 --> focus2_2
    focus3["Proof anchors"]
    page --> focus3
    focus3_1["packages/bijux-canon-runtime"]
    focus3 --> focus3_1
    focus3_2["packages/bijux-canon-runtime/tests"]
    focus3 --> focus3_2
```

## Pages in This Section

- [Package Overview](package-overview.md)
- [Scope and Non-Goals](scope-and-non-goals.md)
- [Ownership Boundary](ownership-boundary.md)
- [Repository Fit](repository-fit.md)
- [Capability Map](capability-map.md)
- [Domain Language](domain-language.md)
- [Lifecycle Overview](lifecycle-overview.md)
- [Dependencies and Adjacencies](dependencies-and-adjacencies.md)
- [Change Principles](change-principles.md)

## Read Across the Package

- [Architecture](../architecture/index.md) when the question becomes structural or execution-oriented
- [Interfaces](../interfaces/index.md) when the question becomes caller-facing or contract-facing
- [Operations](../operations/index.md) when the question becomes procedural, environmental, or release-oriented
- [Quality](../quality/index.md) when the question becomes proof, risk, or review sufficiency

## Concrete Anchors

- `packages/bijux-canon-runtime` as the package root
- `packages/bijux-canon-runtime/src/bijux_canon_runtime` as the import boundary
- `packages/bijux-canon-runtime/tests` as the package proof surface

## Use This Page When

- you need the package idea before the implementation detail
- you are deciding whether work belongs here or in a neighboring package
- you want the shortest honest explanation of what this package is for

## Decision Rule

Use `Foundation` to decide whether a change makes `bijux-canon-runtime` easier or harder to defend as a bounded package. If the work expands package authority without making ownership clearer, stop and re-check the boundary before treating the change as a local improvement.

## Next Checks

- move to architecture when the question becomes structural rather than boundary-oriented
- move to interfaces when the question becomes contract-facing
- move to quality when the question becomes proof or review sufficiency

## Update This Page When

- package ownership moves between this package and a neighboring one
- the package description, core outputs, or boundary modules materially change
- tests or docs reveal that the old boundary explanation is no longer accurate

## What This Page Answers

- what problem `bijux-canon-runtime` is supposed to own on purpose
- where the package boundary stops, even when nearby code looks tempting
- which neighboring package seams deserve comparison before the boundary is changed

## Reviewer Lens

- compare the stated boundary with the modules, artifacts, and tests that are supposed to uphold it
- check that out-of-scope behavior is not quietly re-entering through convenience paths
- confirm that the package story still matches the real repository layout and neighboring package docs

## Honesty Boundary

This page can explain the intended boundary of `bijux-canon-runtime`, but it cannot prove that boundary by itself. The real proof still lives in the code, tests, and neighboring package seams that either support or contradict the story told here.

## Section Contract

- define what the foundation section covers for bijux-canon-runtime
- point readers to the topic pages that hold the detailed explanations
- keep the section boundary reviewable as the package evolves

## Reading Advice

- start here when you know the package but not yet the right page inside the section
- use the page list to choose the narrowest topic that matches the current question
- move across sections only after this section stops being the right lens

## Purpose

This page explains how to use the foundation section for `bijux-canon-runtime` without repeating the detail that belongs on the topic pages beneath it.

## Stability

This page is part of the canonical package docs spine. Keep it aligned with the current package boundary and the topic pages in this section.

## What Good Looks Like

Use these points as the fast check for whether the page is doing real explanatory work.

- `Foundation` leaves a reviewer able to explain `bijux-canon-runtime` in one boundary sentence without hand-waving
- the owned and out-of-scope areas read as complementary rather than contradictory
- neighboring packages become easier to place because this package is clearly bounded

## Failure Signals

These are the quickest signs that the page is drifting from honest explanation into noise or stale certainty.

- `Foundation` has to explain the same ownership claim with repeated exceptions
- the out-of-scope list starts looking like shadow ownership instead of a real boundary
- review conversations keep falling back to package adjacency rather than package intent

## Tradeoffs To Hold

A strong page names the tensions it is managing instead of pretending every desirable goal improves together.

- prefer clean ownership over local convenience, even when nearby code looks easier to reuse
- prefer an explicit boundary gap over a shadow responsibility that no package clearly owns
- prefer keeping `bijux-canon-runtime` intelligible as a bounded package over making it look universally useful

## Cross Implications

- changes here influence how neighboring packages are allowed to stay narrow around `bijux-canon-runtime`
- a weak boundary explanation raises architectural and quality ambiguity immediately
- interface and operations pages inherit confusion when foundational ownership is unclear

## Approval Questions

A reviewer should be able to answer these clearly before trusting the page or the change it is helping to explain.

- does `Foundation` still let a reviewer state `bijux-canon-runtime` ownership in one clear sentence
- does the change preserve package boundaries without creating shadow scope in a neighbor
- is there concrete code and test evidence behind the boundary claim, or only persuasive prose

## Evidence Checklist

Check these assets before trusting the prose. They are the concrete places where the page either holds up or falls apart.

- read the owned module roots under `packages/bijux-canon-runtime/src/bijux_canon_runtime` with the boundary statement in mind
- inspect `packages/bijux-canon-runtime/tests` for proof that the boundary is enforced instead of merely described
- check whether adjacent package docs now tell a conflicting ownership story

## Anti-Patterns

These patterns make documentation feel fuller while quietly making it less clear, less honest, or less durable.

- using package adjacency as a substitute for package ownership
- letting boundary exceptions accumulate until they become the real rule
- writing boundary prose that cannot be checked against code or tests

## Escalate When

These conditions mean the problem is larger than a local wording fix and needs a wider review conversation.

- the page can no longer explain ownership without repeated cross-package caveats
- a change proposal would shift authority between packages rather than stay local
- tests and docs disagree on who is supposed to own the behavior

## Core Claim

The core foundational claim of `bijux-canon-runtime` is that its ownership can be explained as a deliberate package boundary, not as an accident of where code happened to accumulate.

## Why It Matters

If the foundation pages for `bijux-canon-runtime` are weak, reviewers stop knowing where the package really begins and ends. Adjacent packages then absorb behavior by convenience instead of by design.

## If It Drifts

- ownership starts migrating by convenience instead of by explicit package boundary
- neighboring packages inherit responsibilities without deliberate review
- reviewers lose confidence that the package description still means anything stable

## Representative Scenario

A contributor proposes moving new behavior into `bijux-canon-runtime` because it is nearby in the repository. This page should make it obvious whether that work fits the package boundary or belongs in a neighboring package instead.

## Source Of Truth Order

- `packages/bijux-canon-runtime/src/bijux_canon_runtime` for the real ownership boundary in code
- `packages/bijux-canon-runtime/tests` for executable proof that the boundary still holds under change
- `packages/bijux-canon-runtime/README.md` plus this section for the shortest maintained explanation of that boundary

## Common Misreadings

- that `bijux-canon-runtime` owns any nearby behavior just because it would be convenient
- that a boundary statement is enough even when code and tests tell a different story
- that out-of-scope means unimportant rather than intentionally owned elsewhere
