---
title: Known Limitations
audience: mixed
type: reference
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Known Limitations

The package provides deterministic preparation primitives and reference
retrieval components. It is not a document understanding service, a durable
distributed queue, or a guarantee that an external embedding model is stable.

## Model and retrieval limits

- `HashEmbedder` is a dependency-free deterministic baseline. Its vectors are
  not semantically meaningful and must not be used as evidence of retrieval
  quality.
- `SentenceTransformersEmbedder` is optional, loads its model lazily, and
  inherits model availability, version, hardware, and upstream numerical
  behavior. Pin and record those inputs for reproducible work.
- The in-package dense and lexical indexes are reference implementations for
  preparation and evaluation. Use `bijux-canon-index` when backend capability
  negotiation, governed execution, or replayable retrieval is required.
- An embedding dimension is enforced only when an `EmbeddingSpec` is available
  at the embedding/index boundary. A bare `Chunk` does not infer model truth
  from vector length.

## Pipeline limits

- The minimal lazy pipeline filters, cleans, chunks, and embeds without the
  structural deduplication performed by the document-oriented pipeline. Choose
  the API by its documented contract; do not assume all entry points
  materialize identical post-processing.
- Document observations require materialization. Their memory use grows with
  the input and produced chunk count.
- Chunk offsets are Python string offsets in normalized text. They are not byte
  offsets into the original file and may no longer align after whitespace or
  case normalization.
- Structural deduplication recognizes structural equality. It does not detect
  paraphrases, near-duplicates, copied ideas, or semantically equivalent text.
- The package does not promise exactly-once distributed processing. Callers
  integrating queues or remote stores must supply idempotency and transaction
  semantics appropriate to those systems.

## Operational limits

Retries, circuit breakers, memoization, resource management, and async
resilience are explicit combinators. The core pipeline does not silently wrap
external work with them. This preserves visible semantics but means production
integrations must choose and configure their own policies.

The standard retry helpers are bounded only by the policy supplied to them.
Caching changes memory or disk retention and requires a sound cache key.
Circuit breakers can emit errors or truncate streams depending on the selected
variant; truncation must not be mistaken for successful completeness.

## Input and contract limits

Strict interface models reject unknown fields and invalid embeddings, but they
cannot establish that source text is accurate, licensed, safe, or suitable for
a downstream decision. Filtering rules encode caller policy; they are not a
substitute for source governance.

When these limits matter, retain the source identifier, normalization and
chunking configuration, embedding specification, adapter versions, and
observations with the produced chunks. That record makes a later discrepancy
diagnosable even when the package cannot eliminate the external uncertainty.
