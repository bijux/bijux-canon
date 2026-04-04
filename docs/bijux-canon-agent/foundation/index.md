---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Foundation

Start the bijux-canon-agent handbook here when you need the package in one honest sentence: what it owns, why it exists, and where its boundary stops.

These pages establish the durable idea of `bijux-canon-agent`. A reader should be able to skim this section and understand why the package exists, what neighboring packages should not assume about it, and which claims are worth defending during review.

Read the foundation pages for `bijux-canon-agent` as the package's durable self-description. They should let a reader understand the package without needing to reconstruct its purpose from recent implementation history.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-agent"] --> section["Foundation"]
    section --> page["Foundation"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Foundation"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["agent role implementations and role-specific helpers"]
    focus1 --> focus1_1
    focus1_2["deterministic orchestration of the local agent pipeline"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_agent/agents"]
    focus2 --> focus2_1
    focus2_2["trace-backed final outputs"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Foundation"]
    focus3 --> focus3_1
    focus3_2["tests/unit for local behavior and utility coverage"]
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

- `packages/bijux-canon-agent` as the package root
- `packages/bijux-canon-agent/src/bijux_canon_agent` as the import boundary
- `packages/bijux-canon-agent/tests` as the package proof surface

## Use This Page When

- you need the package idea before the implementation detail
- you are deciding whether work belongs here or in a neighboring package
- you want the shortest honest explanation of what this package is for

## Decision Rule

Use `Foundation` to decide whether a change makes `bijux-canon-agent` easier or harder to defend as a bounded package. If the work expands package authority without making ownership clearer, stop and re-check the boundary before treating the change as a local improvement.

## Next Checks

- move to architecture when the question becomes structural rather than boundary-oriented
- move to interfaces when the question becomes contract-facing
- move to quality when the question becomes proof or review sufficiency

## Update This Page When

- package ownership moves between this package and a neighboring one
- the package description, core outputs, or boundary modules materially change
- tests or docs reveal that the old boundary explanation is no longer accurate

## What This Page Answers

- what problem `bijux-canon-agent` is supposed to own on purpose
- where the package boundary stops, even when nearby code looks tempting
- which neighboring package seams deserve comparison before the boundary is changed

## Reviewer Lens

- compare the stated boundary with the modules, artifacts, and tests that are supposed to uphold it
- check that out-of-scope behavior is not quietly re-entering through convenience paths
- confirm that the package story still matches the real repository layout and neighboring package docs

## Honesty Boundary

This page can explain the intended boundary of bijux-canon-agent, but it does not replace the code and tests that ultimately prove that boundary.

## Section Contract

- define what the foundation section covers for bijux-canon-agent
- point readers to the topic pages that hold the detailed explanations
- keep the section boundary reviewable as the package evolves

## Reading Advice

- start here when you know the package but not yet the right page inside the section
- use the page list to choose the narrowest topic that matches the current question
- move across sections only after this section stops being the right lens

## Purpose

This page explains how to use the foundation section for `bijux-canon-agent` without repeating the detail that belongs on the topic pages beneath it.

## Stability

This page is part of the canonical package docs spine. Keep it aligned with the current package boundary and the topic pages in this section.

## What Good Looks Like

- `Foundation` leaves a reviewer able to explain `bijux-canon-agent` in one boundary sentence without hand-waving
- the owned and out-of-scope areas read as complementary rather than contradictory
- neighboring packages become easier to place because this package is clearly bounded

## Failure Signals

- `Foundation` has to explain the same ownership claim with repeated exceptions
- the out-of-scope list starts looking like shadow ownership instead of a real boundary
- review conversations keep falling back to package adjacency rather than package intent

## Tradeoffs To Hold

- prefer clean ownership over local convenience, even when a nearby package looks easier to reuse
- prefer an explicit boundary gap over a shadow responsibility that no package clearly owns
- prefer keeping `bijux-canon-agent` intelligible as a bounded package over making it look universally useful

## Cross Implications

- changes here influence how neighboring packages are allowed to stay narrow around `bijux-canon-agent`
- a weak boundary explanation raises architectural and quality ambiguity immediately
- interface and operations pages inherit confusion when foundational ownership is unclear

## Approval Questions

- does `Foundation` still let a reviewer state `bijux-canon-agent` ownership in one clear sentence
- does the change preserve package boundaries without creating shadow scope in a neighbor
- is there concrete code and test evidence behind the boundary claim rather than prose alone

## Evidence Checklist

- read the owned module roots under `packages/bijux-canon-agent/src/bijux_canon_agent` with the boundary statement in mind
- inspect `packages/bijux-canon-agent/tests` for proof that the boundary is enforced instead of merely described
- check whether adjacent package docs now tell a conflicting ownership story

## Anti-Patterns

- using package adjacency as a substitute for package ownership
- letting boundary exceptions accumulate until they become the real rule
- writing boundary prose that cannot be checked against code or tests

## Escalate When

- the page can no longer explain ownership without repeated cross-package caveats
- a change proposal would shift authority between packages rather than stay local
- tests and docs disagree on who is supposed to own the behavior

## Core Claim

The foundational claim of `bijux-canon-agent` is that its package boundary can be explained in stable ownership terms instead of by implementation accident.

## Why It Matters

If the foundation pages for `bijux-canon-agent` are weak, reviewers stop knowing where the package boundary really is and adjacent packages begin absorbing behavior by convenience instead of design.

## If It Drifts

- ownership starts migrating by convenience instead of by explicit package boundary
- neighboring packages inherit responsibilities without deliberate review
- reviewers lose confidence that the package description still means anything stable

## Representative Scenario

A contributor proposes moving new behavior into `bijux-canon-agent` because it is nearby in the repository. This page should make it obvious whether that work fits the package boundary or belongs in a neighboring package instead.

## Source Of Truth Order

- `packages/bijux-canon-agent/src/bijux_canon_agent` for the real ownership boundary in code
- `packages/bijux-canon-agent/tests` for executable proof of that boundary
- `packages/bijux-canon-agent/README.md` and this section for the shortest maintained framing

## Common Misreadings

- that `bijux-canon-agent` owns any nearby behavior just because it is convenient
- that a boundary statement is enough without the code and tests that enforce it
- that out-of-scope means unimportant rather than owned elsewhere
