# bijux-canon-ingest

> At a glance: **ingest -> index -> retrieve -> answer** • deterministic chunk IDs and index fingerprints • CLI + FastAPI interfaces • explicit sync and asyncio effect surfaces

**Docs:** https://bijux.github.io/bijux-canon-ingest/  
**PyPI:** https://pypi.org/project/bijux-canon-ingest/  
**Issues:** https://github.com/bijux/bijux-canon/issues  
**Changelog:** https://github.com/bijux/bijux-canon/blob/main/packages/bijux-canon-ingest/CHANGELOG.md

`bijux-canon-ingest` focuses on deterministic document ingestion, persisted index building, retrieval, and grounded answer assembly. The package keeps document processing pure where possible, pushes I/O into explicit adapters and effect descriptions, and keeps operational concerns such as retries, tracing, and resource safety in clearly named support modules.

## Highlights

- Functional core for cleaning, chunking, embedding, retrieval, and answer assembly.
- Explicit orchestration in `application/`, with transport adapters in `interfaces/`.
- Dedicated `observability/`, `integrations/`, and `safeguards/` packages for cross-cutting concerns.
- Synchronous `IOPlan` and asyncio-based async effects for deterministic testing and controlled runtime behavior.

## Installation

```bash
pip install bijux-canon-ingest
```

## Quick Start

Build an index from CSV:

```bash
bijux-canon-ingest index build --input corpus.csv --out index.msgpack --backend bm25
```

Retrieve supporting chunks:

```bash
bijux-canon-ingest retrieve --index index.msgpack --query "what is bm25?"
```

Ask for a grounded answer with citations:

```bash
bijux-canon-ingest ask --index index.msgpack --query "what is bm25?" --top-k 5
```

Programmatic indexing example:

```python
from bijux_canon_ingest.application.indexing import ingest_docs_to_chunks
from bijux_canon_ingest.core.types import RagEnv, RawDoc

docs = [
    RawDoc(doc_id="1", title="Example", abstract="Sample text.", categories="docs")
]
chunks = ingest_docs_to_chunks(docs=docs, env=RagEnv(chunk_size=256))
print(chunks[0].text)
```

Asyncio effect example:

```python
from bijux_canon_ingest.domain.effects.asyncio import async_gen_map, resilient_mapper

mapper = resilient_mapper(embed_fn, RetryPolicy(max_attempts=3))
stream = async_gen_map(source_stream, mapper)
```

See [Project Tree & Guide](project_overview.md), [Architecture Overview](architecture/index.md), and [CLI Reference](reference/cli.md) for the current package layout and entrypoints.
