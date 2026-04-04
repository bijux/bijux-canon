---
title: Command Surfaces
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Command Surfaces

Some compatibility packages also preserve historic command names so migration
does not break operator scripts immediately.

These compatibility pages should make legacy names understandable without romanticizing them. Their value is in clarifying preservation, migration, and retirement pressure with as little ambiguity as possible.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Compatibility Handbook"]
    section --> page["Command Surfaces"]
    dest1["legacy package names"]
    dest2["migration decisions"]
    dest3["retirement review"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Command Surfaces"]
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

## Command Rule

A compatibility command should only exist when the canonical package still
provides a meaningful route behind it.

## Concrete Anchors

- `packages/compat-*` for the preserved legacy packages
- the compatibility package `README.md` files for canonical targets
- the matching canonical package docs for current behavior and new work

## Use This Page When

- you are tracing a legacy package name back to its canonical replacement
- you need migration guidance rather than product implementation detail
- you are deciding whether a compatibility surface still deserves to exist

## Decision Rule

Use `Command Surfaces` to decide whether a preserved legacy name is still serving a real migration need. If the only reason to keep it is habit rather than an identified dependent environment, the section should bias the reviewer toward migration or retirement planning.

## What This Page Answers

- which legacy surface is still preserved
- when new work should move to the canonical package instead
- what evidence would justify retiring a compatibility package

## Reviewer Lens

- compare legacy names here with the compatibility package metadata and README targets
- check that migration advice still points at current canonical docs
- confirm that compatibility language does not accidentally encourage new work to start here

## Next Checks

- move to the canonical package docs once the current target package is known
- inspect compatibility package metadata if the question is about what remains preserved
- use this section again only when evaluating migration progress or retirement readiness

## Update This Page When

- a legacy package is added, retired, or repointed to a different canonical target
- migration guidance becomes stale compared with the current package set
- compatibility scope changes materially enough to affect retirement decisions

## Honesty Boundary

This section documents preserved legacy surfaces, but it does not claim those legacy names are the preferred place for new work or long-term design growth.

## Purpose

This page records the intent behind legacy command preservation.

## Stability

Keep it aligned with the command declarations in compatibility package metadata.

## What Good Looks Like

- `Command Surfaces` makes the legacy-to-canonical path obvious
- migration pressure is clearer than nostalgia for old package names
- retirement can be discussed from evidence rather than from vague discomfort

## Failure Signals

- `Command Surfaces` spends more time defending legacy names than clarifying migration
- the canonical target is harder to find than the old name
- retirement conversations keep stalling because the remaining need is not described concretely

## Cross Implications

- unclear compatibility pages slow adoption of the canonical package docs
- retirement planning becomes harder because repository and package owners lack one shared migration story
- legacy naming pressure can distort product package expectations if it is not kept explicitly separate

## Evidence Checklist

- inspect the relevant `packages/compat-*` metadata and README files
- check the canonical target package docs named by this page
- confirm there is still a real migration consumer before accepting preservation as necessary

## Core Claim

Each compatibility page should make migration pressure clearer than legacy habit, so preserved names remain understandable without becoming a second product line.

## Why It Matters

Compatibility pages matter because legacy package names often survive longer than the people who remember why they exist, and that makes migration drift expensive.

## If It Drifts

- legacy names become easier to keep using than to migrate away from
- canonical targets become ambiguous in old automation or docs
- retirement decisions get delayed because the actual migration state is unclear

## Representative Scenario

A legacy dependency name appears in an old environment file. The compatibility docs should let a maintainer map it to the canonical package and judge whether that old name still deserves to survive.

## Source Of Truth Order

- the `packages/compat-*` metadata and README files for preserved legacy surfaces
- the matching canonical package docs for current behavior
- this section for the migration and retirement explanation that ties them together

## Common Misreadings

- that legacy names are still the preferred public names
- that compatibility packages should grow like first-class product packages
- that preserved import or distribution names prove long-term architectural importance
