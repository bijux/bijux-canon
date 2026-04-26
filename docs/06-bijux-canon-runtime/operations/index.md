---
title: Operations
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Operations

Open this section to install, run, diagnose, and release
`bijux-canon-runtime` from checked-in workflow guidance instead of team
memory.

These pages are the checked-in operating memory for `bijux-canon-runtime`.
They should let a maintainer move from setup to diagnosis to release without
relying on CI archaeology or private habits.

Runtime operations are high-consequence because replay stores, verification
policy, and durable traces can turn a sloppy rerun into a misleading record.
This section shows how to operate the package carefully, not merely how
to invoke it.

## Start Here

- open [Common Workflows](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/common-workflows/) when the real question is how to
  run the governed path safely
- open [Observability and Diagnostics](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/observability-and-diagnostics/) when
  you need to inspect replay, store, or trace behavior
- open [Failure Recovery](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/failure-recovery/) when a persisted or replayed run
  has diverged
- open [Security and Safety](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/security-and-safety/) before broadening runtime
  authority or store access

## Pages In This Section

- [Installation and Setup](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/installation-and-setup/)
- [Local Development](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/local-development/)
- [Common Workflows](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/common-workflows/)
- [Observability and Diagnostics](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/observability-and-diagnostics/)
- [Performance and Scaling](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/performance-and-scaling/)
- [Failure Recovery](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/failure-recovery/)
- [Release and Versioning](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/release-and-versioning/)
- [Security and Safety](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/security-and-safety/)
- [Deployment Boundaries](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/deployment-boundaries/)

## Open This Section When

- you are installing, running, diagnosing, or releasing the package
- you need repeatable operational anchors rather than architectural framing
- you are responding to package behavior in local work, CI, or incident pressure

## Open Another Section When

- the real question is why runtime has authority in the first place
- you need schema or artifact contract detail rather than procedure
- you are deciding whether the proof bar is high enough rather than how to run
  it

## Concrete Anchors

- `packages/bijux-canon-runtime/pyproject.toml` for package metadata and
  install surfaces
- `src/bijux_canon_runtime/interfaces/cli/` for operator commands
- `src/bijux_canon_runtime/observability/storage/` for store and schema
  concerns that affect operations directly
- `tests/e2e/` and `tests/regression/` for the repeatable operational backstops
  that defend replay and recovery behavior

## Across This Package

- open [Interfaces](https://bijux.io/bijux-canon/06-bijux-canon-runtime/interfaces/) when an operational question turns
  into a CLI, API, or schema contract question
- open [Architecture](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/) when a recovery question really
  depends on execution or storage structure
- open [Quality](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/) when the real issue is whether the
  workflow is sufficiently defended and reviewed

## Bottom Line

Open this section to decide whether a maintainer can repeat runtime workflow
from checked-in assets instead of memory. If a step works only because someone
already knows the trick, the package is not documented clearly enough yet.

