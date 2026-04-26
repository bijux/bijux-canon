---
title: Architecture
audience: mixed
type: index
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Architecture

Open this section when the important question is how ingest is put together:
which modules shape source material, where deterministic transforms happen, and
how prepared output reaches the retrieval handoff without hidden shortcuts.

These pages help you trace real execution flow through named parts of the
package instead of inferring architecture from file names alone. The goal is
clarity about structure, not decorative system language.

## Start Here

- open [Module Map](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/module-map/) for the shortest guide to which directory
  owns which architectural responsibility
- open [Execution Model](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/execution-model/) when the hard question is how
  source material moves from input to prepared output
- open [Integration Seams](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/integration-seams/) when a change might blur the
  line between ingest and its upstream or downstream neighbors

## Pages In This Section

- [Module Map](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/module-map/)
- [Dependency Direction](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/dependency-direction/)
- [Execution Model](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/execution-model/)
- [State and Persistence](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/state-and-persistence/)
- [Integration Seams](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/integration-seams/)
- [Error Model](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/error-model/)
- [Extensibility Model](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/extensibility-model/)
- [Code Navigation](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/code-navigation/)
- [Architecture Risks](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/architecture-risks/)

## Open Architecture When

- you need to trace structural ownership before refactoring ingest internals
- you are checking whether dependency flow still supports deterministic
  preparation
- you need to understand where artifact shaping ends and downstream retrieval
  behavior begins

## Open Another Section When

- the question is mainly about public commands, schemas, or import contracts
- the real issue is operational, such as setup, release, or incident handling
- you need proof and risk posture more than structure and dependency logic

## Read Across The Package

- open [Foundation](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/) when the structural question is
  really an ownership question
- open [Interfaces](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/) when architecture reaches a caller
  or artifact contract
- open [Operations](https://bijux.io/bijux-canon/02-bijux-canon-ingest/operations/) when structural decisions affect
  repeatable maintainer workflows
- open [Quality](https://bijux.io/bijux-canon/02-bijux-canon-ingest/quality/) when you need proof that the documented
  design is still defended in tests and review

## Concrete Anchors

- `src/bijux_canon_ingest/processing` for deterministic document transforms
- `src/bijux_canon_ingest/retrieval` for retrieval-oriented models and assembly
- `src/bijux_canon_ingest/application` for package workflows

## Bottom Line

Open `Architecture` to make the internal flow legible enough that a reviewer can
say where ingest logic lives and why. If the code only works because the
structure is hard to explain, the architecture has already started to drift.

