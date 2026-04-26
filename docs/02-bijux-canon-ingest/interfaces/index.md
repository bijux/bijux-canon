---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Interfaces

Open this section when you need to know which ingest surfaces are real
contracts: commands, schemas, imports, artifacts, and examples that callers
or downstream packages can rely on without guessing.

These pages keep accidental dependencies from hardening around incidental
implementation details. For ingest, that matters because chunk shape,
artifact layout, and operator entrypoints become downstream assumptions very
quickly once other packages start depending on them.

## Visual Summary

```mermaid
flowchart LR
    caller["reader or downstream caller"]
    cli["CLI workflows<br/>start ingest runs"]
    schema["schemas and data contracts<br/>define prepared output"]
    artifacts["artifact contracts<br/>what files downstream packages trust"]
    imports["public imports<br/>supported Python entrypoints"]
    review["compatibility review<br/>what changes need extra care"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class caller,page review;
    class cli,schema,artifacts positive;
    class imports anchor;
    class review action;
    caller --> cli
    caller --> schema
    caller --> artifacts
    caller --> imports
    caller --> review
```

## Start Here

- open [CLI Surface](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/cli-surface/) when the issue begins with an ingest
  command or operator entrypoint
- open [Data Contracts](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/data-contracts/) when the question is about chunk
  shapes, records, or prepared payload structure
- open [Artifact Contracts](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/artifact-contracts/) when downstream work depends
  on specific ingest outputs staying stable
- open [Compatibility Commitments](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/compatibility-commitments/) when a change
  might break an established ingest-facing contract

## Pages In This Section

- [CLI Surface](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/cli-surface/)
- [API Surface](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/api-surface/)
- [Configuration Surface](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/configuration-surface/)
- [Data Contracts](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/data-contracts/)
- [Artifact Contracts](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/artifact-contracts/)
- [Entrypoints and Examples](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/entrypoints-and-examples/)
- [Operator Workflows](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/operator-workflows/)
- [Public Imports](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/public-imports/)
- [Compatibility Commitments](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/compatibility-commitments/)

## Open Interfaces When

- you need to know which ingest surface is intentional rather than incidental
- downstream retrieval or orchestration work depends on prepared ingest outputs
- you are reviewing whether a change adds compatibility pressure to an exposed
  command, artifact, or schema

## Open Another Section When

- the real question is why ingest owns the work in the first place
- you need internal structure, dependency direction, or execution flow
- the issue is about setup, diagnostics, or release workflow rather than
  caller-facing contract surfaces

## Read Across The Package

- open [Foundation](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/) when a contract question is really
  a package-boundary question
- open [Architecture](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/) when the surface depends on
  structural flow through processing or retrieval modules
- open [Operations](https://bijux.io/bijux-canon/02-bijux-canon-ingest/operations/) when you need repeatable commands,
  setup, or maintainer runbooks
- open [Quality](https://bijux.io/bijux-canon/02-bijux-canon-ingest/quality/) when the real question is whether the
  documented contract is sufficiently defended

## Concrete Anchors

- CLI entrypoint in `src/bijux_canon_ingest/interfaces/cli/entrypoint.py`
- HTTP boundaries under `src/bijux_canon_ingest/interfaces`
- configuration modules under `src/bijux_canon_ingest/config`
- `apis/bijux-canon-ingest/v1/schema.yaml`

## Bottom Line

Open `Interfaces` to separate what ingest truly promises from what merely
happens to be visible today. If a downstream dependency cannot be defended in
terms of named commands, schemas, artifacts, examples, and tests, it is not yet
a stable contract.

