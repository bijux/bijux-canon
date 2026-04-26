---
title: Architecture
audience: mixed
type: index
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Architecture

Use this section when the important question is how ingest is put together:
which modules shape source material, where deterministic transforms happen, and
how prepared output reaches the retrieval handoff without hidden shortcuts.

These pages should help reviewers and maintainers trace real execution flow
through named parts of the package instead of inferring architecture from file
names alone. The goal is clarity about structure, not decorative system
language.

## Visual Summary

```mermaid
flowchart LR
    source["source material enters ingest"]
    app["application workflows<br/>coordinate ingest runs"]
    processing["processing modules<br/>transform and chunk"]
    retrieval["retrieval-ready models<br/>shape downstream handoff"]
    artifacts["durable ingest artifacts"]
    seams["integration seams<br/>upstream documents and downstream index"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class source,page artifacts;
    class app,processing,retrieval positive;
    class seams caution;
    source --> app --> processing --> retrieval --> artifacts
    source --> seams
    artifacts --> seams
```

## Start Here

- open [Module Map](module-map.md) for the shortest guide to which directory
  owns which architectural responsibility
- open [Execution Model](execution-model.md) when the hard question is how
  source material moves from input to prepared output
- open [Integration Seams](integration-seams.md) when a change might blur the
  line between ingest and its upstream or downstream neighbors

## Pages In This Section

- [Module Map](module-map.md)
- [Dependency Direction](dependency-direction.md)
- [Execution Model](execution-model.md)
- [State and Persistence](state-and-persistence.md)
- [Integration Seams](integration-seams.md)
- [Error Model](error-model.md)
- [Extensibility Model](extensibility-model.md)
- [Code Navigation](code-navigation.md)
- [Architecture Risks](architecture-risks.md)

## Use This Section When

- you need to trace structural ownership before refactoring ingest internals
- you are checking whether dependency flow still supports deterministic
  preparation
- you need to understand where artifact shaping ends and downstream retrieval
  behavior begins

## Do Not Use This Section When

- the question is mainly about public commands, schemas, or import contracts
- the real issue is operational, such as setup, release, or incident handling
- you need proof and risk posture more than structure and dependency logic

## Read Across The Package

- open [Foundation](../foundation/index.md) when the structural question is
  really an ownership question
- open [Interfaces](../interfaces/index.md) when architecture reaches a caller
  or artifact contract
- open [Operations](../operations/index.md) when structural decisions affect
  repeatable maintainer workflows
- open [Quality](../quality/index.md) when you need proof that the documented
  design is still defended in tests and review

## Concrete Anchors

- `src/bijux_canon_ingest/processing` for deterministic document transforms
- `src/bijux_canon_ingest/retrieval` for retrieval-oriented models and assembly
- `src/bijux_canon_ingest/application` for package workflows

## Reader Takeaway

Use `Architecture` to make the internal flow legible enough that a reviewer can
say where ingest logic lives and why. If the code only works because the
structure is hard to explain, the architecture has already started to drift.

## Purpose

This page introduces the architecture handbook for `bijux-canon-ingest` and
routes readers to the module, execution, seam, and risk pages that explain how
the package is actually organized.
