# Canonical Query Contract

This contract defines how query results are ordered, filtered, and serialized across **all** backends. Every backend and adapter must conform.

## Ordering (Exact)

- Primary sort: **ascending distance** (lower is better).
- Tie-breaker: **stable order** by `(distance, vector_id, chunk_id, document_id)`.
- Output ranks are **1-based** and must reflect the final ordered list.

## Distance Precision

- Distances are computed and emitted as `float` values.
- Backends must normalize to **float32-equivalent precision** before sorting.
- If a backend uses higher precision internally, it must round to float32-equivalent for ordering.

## Top-K Rules

- If fewer than `k` results exist, return **all** results.
- If `k <= 0`, reject the request.
- `k` applies **after** ordering and filtering.

## Filtering Semantics

Canonical filter shape (JSON):

```
{
  "doc_id": "...",
  "chunk_id": "...",
  "source_uri": "...",
  "tags": ["..."]
}
```

- `doc_id`, `chunk_id`, `source_uri` accept either a single string or a list.
- `tags` must be a list; all tags must be present to match.
- If a backend supports filters, the filter **must be pushed down**.
- If a backend does not support filters, **post-filter** in memory and log a warning.
- Unsupported filter keys must be rejected.

## ANN / Non-Deterministic Mode

- ANN results may deviate, but **ordering must still use the same tie-break rules**.
- If a backend cannot satisfy the requested mode (exact vs ANN), it must **refuse**.

## Consistency Semantics

Each backend declares its consistency model in capabilities and provenance:

- `read_after_write` for local stores (e.g., memory, sqlite, faiss)
- `eventual` for remote stores (e.g., qdrant)

Backends must not claim stronger guarantees than they provide.
