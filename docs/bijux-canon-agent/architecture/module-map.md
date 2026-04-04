---
title: Module Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Module Map

The architecture of `bijux-canon-agent` becomes readable when its major module
groups are treated as responsibilities instead of as folders. This page should
help a reviewer move from a question about behavior to the part of the package
most likely to answer it.

When this page is useful, code reading becomes targeted rather than exploratory.

Read the architecture pages for `bijux-canon-agent` as a reviewer-facing map of structure and flow. They should shorten code reading, not try to replace it, and they should make drift visible before it becomes surprising.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-agent"] --> section["Architecture"]
    section --> page["Module Map"]
    dest1["trace execution"]
    dest2["spot dependency pressure"]
    dest3["judge structural drift"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Module Map"]
    focus1["Module groups"]
    page --> focus1
    focus1_1["role-local behavior"]
    focus1 --> focus1_1
    focus1_2["execution flow orchestration"]
    focus1 --> focus1_2
    focus2["Read in code"]
    page --> focus2
    focus2_1["src/bijux_canon_agent/agents"]
    focus2 --> focus2_1
    focus2_2["src/bijux_canon_agent/pipeline"]
    focus2 --> focus2_2
    focus3["Design pressure"]
    page --> focus3
    focus3_1["Module Map"]
    focus3 --> focus3_1
    focus3_2["tests/unit for local behavior and utility coverage"]
    focus3 --> focus3_2
```

## Major Modules

- `src/bijux_canon_agent/agents` for role-local behavior
- `src/bijux_canon_agent/pipeline` for execution flow orchestration
- `src/bijux_canon_agent/application` for workflow policy and graph logic
- `src/bijux_canon_agent/llm` for LLM runtime integration support
- `src/bijux_canon_agent/interfaces` for CLI boundaries and operator helpers
- `src/bijux_canon_agent/traces` for trace-facing models and persistence helpers

## Concrete Anchors

- `src/bijux_canon_agent/agents` for role-local behavior
- `src/bijux_canon_agent/pipeline` for execution flow orchestration
- `src/bijux_canon_agent/application` for workflow policy and graph logic

## Use This Page When

- you are tracing structure, execution flow, or dependency pressure
- you need to understand how modules fit before refactoring
- you are reviewing design drift rather than one isolated bug

## Decision Rule

Use `Module Map` to decide whether a structural change makes `bijux-canon-agent` easier or harder to explain in terms of modules, dependency direction, and execution flow. If the change works only because the design becomes harder to read, the safer answer is redesign rather than acceptance.

## Next Checks

- move to interfaces when the review reaches a public or operator-facing seam
- move to operations when the concern becomes repeatable runtime behavior
- move to quality when you need proof that the documented structure is still protected

## Update This Page When

- module responsibilities or dependency direction change materially
- new execution pathways or structural seams become important to review
- architectural risk shifts enough that the current map is misleading

## What This Page Answers

- how `bijux-canon-agent` is organized internally in terms a reviewer can follow
- which modules carry the main execution and dependency story
- where structural drift would show up before it becomes expensive

## Reviewer Lens

- trace the described execution path through the named modules instead of trusting the diagram alone
- look for dependency direction or layering that now contradicts the documented seam
- verify that the structural risks named here still match the current code shape

## Honesty Boundary

This page describes the current structural model of `bijux-canon-agent`, but it does not guarantee that every import path or runtime path still obeys that model. Readers should treat it as a map that must stay aligned with code and tests, not as an authority above them.

## Purpose

This page provides a shortest-path code map for the package.

## Stability

Keep it aligned with the actual source directories under `packages/bijux-canon-agent`.

## What Good Looks Like

- `Module Map` lets a reviewer trace structure without guessing where the real pathway lives
- the documented module relationships make refactors easier to reason about before code is changed
- the page shortens code reading by pointing at the right structural hotspots first

## Failure Signals

- `Module Map` points to modules that no longer carry the behavior the page claims they do
- dependency direction has to be explained with caveats instead of a clean structural story
- the path from interface to domain to proof no longer feels traceable in one pass

## Tradeoffs To Hold

- prefer clean dependency direction over short-term coupling that makes one change easier today
- prefer an execution path that can be explained quickly over indirection that only looks flexible
- prefer structural legibility in `bijux-canon-agent` over squeezing unrelated behavior into the same module seam

## Cross Implications

- changes here alter how interface, operations, and quality pages for `bijux-canon-agent` should be read
- structural drift often becomes visible in caller-facing seams before it is obvious in prose
- quality expectations need to move when the architecture adds new execution or dependency pressure

## Approval Questions

- does `Module Map` still describe a structure that a reviewer can trace without caveats
- is dependency direction cleaner or at least no less legible after the change
- can the claimed execution path still be matched to concrete modules, seams, and proof assets

## Evidence Checklist

- open the listed structural modules in `packages/bijux-canon-agent/src/bijux_canon_agent` and trace whether they still match the page narrative
- inspect `packages/bijux-canon-agent/tests` for regressions that reveal changed execution or dependency structure
- compare the documented hotspots with the actual changed files in the review

## Anti-Patterns

- explaining structure with diagrams that no longer match the modules listed
- treating temporary implementation shortcuts as if they were enduring architectural seams
- allowing dependency direction to drift because the code still happens to run

## Escalate When

- the documented structure no longer matches the changed execution path
- a local refactor introduces a dependency direction question that affects other sections
- the review cannot explain the change without redefining a major seam

## Core Claim

The core architectural claim of `bijux-canon-agent` is that its structure is deliberate enough for a reviewer to trace responsibilities, dependencies, and drift pressure without reverse-engineering the whole codebase.

## Why It Matters

If the architecture pages for `bijux-canon-agent` are weak, refactors become guesswork. Dependency drift can hide until it leaks into tests, caller behavior, or operator experience.

## If It Drifts

- dependency direction becomes harder to inspect quickly
- refactors can land without anyone noticing structural regressions until later
- code navigation becomes slower because the documented map no longer matches reality

## Representative Scenario

A reviewer is tracing a refactor through `bijux-canon-agent` and needs to know whether the changed modules still line up with the documented execution and dependency structure.

## Source Of Truth Order

- `packages/bijux-canon-agent/src/bijux_canon_agent` for the actual dependency direction and module structure
- `packages/bijux-canon-agent/tests` for structural and behavioral regressions that reveal drift
- this page for the reviewer-facing map that should stay aligned with those assets

## Common Misreadings

- that the documented module map guarantees every import is still clean automatically
- that the most visible current path is the whole architectural contract
- that diagrams excuse the reader from checking the named modules and tests
