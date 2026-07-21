---
title: Local Development
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Local Development

Develop ingest from the transformation contract outward. The fastest useful
loop identifies which prepared record can change, runs the smallest executable
proof for that invariant, and inspects the resulting identifiers or artifacts
before widening validation.

```mermaid
flowchart LR
    C[Change one ingest invariant] --> F[Run focused test]
    F --> A[Inspect records or artifact]
    A --> B{Public boundary changed?}
    B -- no --> P[Run package gate]
    B -- yes --> D[Update docs or schema]
    D --> P
```

## Bootstrap from the repository root

```bash
make install
make -f makes/packages/bijux-canon-ingest.mk \
  -C packages/bijux-canon-ingest help
```

The package profile creates `packages/bijux-canon-ingest/.venv` when a
package target needs it. Root dispatch keeps the repository configuration and
artifact routing intact:

```bash
make test PACKAGE=bijux-canon-ingest
make lint PACKAGE=bijux-canon-ingest
make quality PACKAGE=bijux-canon-ingest
```

Do not use `make -C packages/bijux-canon-ingest <target>` without the profile
path: the package directory intentionally has no standalone Makefile.

## Run a focused proof first

After the package environment exists, run the narrow test file or node that
owns the changed behavior:

```bash
packages/bijux-canon-ingest/.venv/bin/python -m pytest \
  packages/bijux-canon-ingest/tests/unit/<test-file>.py -q
```

Choose the proof by affected contract:

| Changed behavior | Inspect and test |
| --- | --- |
| cleaning or validation | normalized fields, rejected input, stable document identity |
| chunking | offsets, overlap, tail policy, order, and chunk identity |
| embedding | model descriptor, dimension, normalization, cache provenance, failure path |
| local retrieval | corpus fingerprint, metric, stable rank order, citations, persisted codec |
| streaming or retry | order restoration, backpressure, cancellation, error classification |
| CLI | exit status, structured output, path behavior, and artifact bytes |
| HTTP | request rejection, response schema, OpenAPI drift, and process-local index lifetime |

When a transform changes content or identity, inspect an emitted JSONL or
MessagePack artifact rather than relying only on object assertions. A green
unit test cannot reveal an undocumented wire change by itself.

## Validate public boundaries deliberately

Use the API lane only for request, response, handler, or schema changes:

```bash
make api PACKAGE=bijux-canon-ingest
```

Use `make docs-check` for handbook changes. Use the package build when imports,
package data, entry points, or distribution metadata changed:

```bash
make build PACKAGE=bijux-canon-ingest
```

Generated reports, caches, local indexes, and diagnostic runs belong under
`artifacts/`. Do not place them beside source modules or documentation.

## Finish with reconstructable evidence

Record the input identity, resolved preparation configuration, emitted
artifact fingerprint, and exact focused checks. If retrieval behavior changed,
retain the evaluation corpus and result comparison. If a rejected input now
succeeds—or a formerly valid input is refused—update the relevant failure and
interface documentation in the same change.

See [change validation](../quality/change-validation.md) for risk-to-check
routing and [release and versioning](release-and-versioning.md) for changes that
alter published expectations.
