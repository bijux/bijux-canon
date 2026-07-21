---
title: Public Imports
audience: developers
type: reference
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Public Imports

Import supported application building blocks from `bijux_canon_ingest`. The
package root is the compatibility boundary; implementation modules beneath
`application`, `infra`, `interfaces`, and `processing` may change as ownership
is refined.

## Common Entry Points

| Need | Root imports |
| --- | --- |
| records | `RawDoc`, `CleanDoc`, `ChunkWithoutEmbedding`, `Chunk` |
| processing | `clean_doc`, `chunk_doc`, `embed_chunk`, `structural_dedup_chunks` |
| complete ingestion | `run_ingest_pipeline`, `run_ingest_pipeline_docs`, `run_ingest_pipeline_path` |
| streaming ingestion | `iter_ingest_pipeline`, `iter_ingest_pipeline_core`, `stream_chunks` |
| configuration | `IngestConfig`, `IngestDeps`, `IngestBoundaryDeps`, `build_ingest_deps` |
| explicit outcomes | `Result`, `Ok`, `Err`, `ErrInfo`, `Option`, `Some`, `NONE` |
| safeguards | `retry_map_iter`, circuit breakers, error-report folds, `DiskCache` |
| composition | `Source`, `Transform`, `compose_transforms`, `multicast`, `throttle` |

The root also exposes tree folds, functional composition primitives,
instrumentation, rule predicates, and bounded streaming utilities. Inspect
`bijux_canon_ingest.__all__` when generating API inventory; do not infer support
from names that happen to be reachable.

## Minimal Pipeline

```python
from bijux_canon_ingest import (
    IngestConfig,
    RagEnv,
    RawDoc,
    build_ingest_deps,
    run_ingest_pipeline_docs,
)

documents = [
    RawDoc(
        doc_id="paper-7",
        title="Example",
        abstract="A reproducible source record for ingestion.",
        categories="methods",
    )
]

config = IngestConfig(env=RagEnv(chunk_size=256))
dependencies = build_ingest_deps(config)
chunks, observations = run_ingest_pipeline_docs(documents, config, dependencies)
```

Pipeline and configuration helpers are resolved lazily. Importing the package
root therefore keeps low-level use lightweight while preserving one stable
surface for application callers.

## Boundary-Specific Imports

Some contracts intentionally live below the root because using them opts into
a particular boundary:

```python
from bijux_canon_ingest.interfaces.serialization import (
    ChunkModel,
    deserialize_model,
    serialize_model,
)
from bijux_canon_ingest.retrieval import BM25Index, NumpyCosineIndex
```

Use these documented namespaces only when the boundary matters. Avoid importing
underscore-prefixed modules, `_package_api`, concrete infrastructure adapters,
or CLI parser internals. Those are implementation surfaces, even when Python
can resolve them.

`bijux_rag` forwards the canonical root for compatibility. New integrations
should use `bijux_canon_ingest`; see [Compatibility Commitments](compatibility-commitments.md)
for the migration contract.
