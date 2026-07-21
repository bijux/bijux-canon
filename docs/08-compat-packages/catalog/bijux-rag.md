---
title: bijux-rag
audience: mixed
type: reference
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-07-21
---

# bijux-rag

`bijux-rag` preserves the earlier distribution, import, and command names for
`bijux-canon-ingest`. The canonical package owns source identity,
normalization, chunking, deterministic preparation results, and typed ingest
failures.

Despite the preserved “RAG” name, this bridge does not own vector retrieval,
claim reasoning, or orchestration. Those decisions belong to index, reason,
and agent respectively.

## Identity Contract

| Surface | Preserved identity | Canonical identity |
| --- | --- | --- |
| distribution | `bijux-rag` | `bijux-canon-ingest` |
| Python root | `bijux_rag` | `bijux_canon_ingest` |
| console command | `bijux-rag` | `bijux-canon-ingest` |
| nested CLI module | `bijux_rag.interfaces.cli.entrypoint` | `bijux_canon_ingest.interfaces.cli.entrypoint` |
| representative nested type | `bijux_rag.core.types.RawDoc` | `bijux_canon_ingest.core.types.RawDoc` |

```mermaid
flowchart LR
    source["source bytes or records"]
    legacy["bijux-rag identity"]
    bridge["same-version ingest bridge"]
    output["canonical prepared output"]
    downstream["index, reason, or application"]

    source --> legacy --> bridge --> output --> downstream
```

The built bridge depends on exactly the same version of
`bijux-canon-ingest`. Its public root follows the canonical facade, nested
module aliases return canonical module objects, and its command routes directly
to the ingest entrypoint.

## Existing And Canonical Usage

Existing automation remains callable:

```bash
python -m pip install bijux-rag
bijux-rag --help
python -m bijux_rag --help
```

```python
from bijux_rag import RawDoc
```

The canonical form for new work is:

```bash
python -m pip install bijux-canon-ingest
bijux-canon-ingest --help
```

```python
from bijux_canon_ingest import RawDoc
```

The two `RawDoc` imports identify the same canonical class. An alias import
therefore does not introduce a competing document model.

## Migrate The Whole Preparation Boundary

Replacing the dependency and imports is necessary but may not be sufficient.
Inspect command invocations, source configuration, serialized dotted paths,
prepared artifact readers, cache keys, container images, and downstream code
that assumes an older output layout. Validate a representative document from
source through the first downstream consumer.

Current ingest semantics and supported facade live in the
[ingest handbook](../../02-bijux-canon-ingest/index.md). The bridge proves
delegation and selected identity invariants; it does not certify arbitrary
private paths or every historical prepared artifact.

## Repository Ownership

Current source, issues, release metadata, and documentation are owned by
`bijux/bijux-canon`. Treat the former `bijux/bijux-rag` repository as
historical context rather than a parallel implementation source.

Continue with [command surfaces](command-surfaces.md) for executable behavior
and [migration guidance](../migration/migration-guidance.md) for the full
surface checklist.
