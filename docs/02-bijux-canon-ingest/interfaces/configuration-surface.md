---
title: Configuration Surface
audience: mixed
type: reference
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Configuration Surface

Ingest configuration controls normalization, chunk identity, embedding, local
retrieval, and failure tolerance. Values that affect emitted text, offsets,
vectors, ranking, or accepted records are part of the data contract and belong
with the resulting artifact.

## Library configuration

| Configuration | Important fields | Contract effect |
| --- | --- | --- |
| `CleanConfig` | ordered `rule_names` | Changes normalized text and therefore chunks and identities |
| `RagEnv` | `chunk_size`, `overlap`, `sample_size`, `tail_policy` | Changes chunk boundaries, count, and final-tail behavior |
| `EmbeddingSpec` | `model`, `dim`, `metric`, `normalized` | Defines vector compatibility at index boundaries |
| `RulesConfig` and predicates | allowed document fields and predicate tree | Changes which sources enter the corpus |
| `PipelineConfig` | ordered `StepConfig` values | Defines the transformation topology and per-stage parameters |
| retry and breaker parameters | attempts, rate/count thresholds, delay policy | Changes continuation and partial-failure behavior |

The default cleaner applies `strip`, `lower`, and `collapse_ws` in that order.
Available named rules also include `upper` and `replace_newlines`. Rule order is
observable: retain the ordered tuple rather than treating it as a set.

## Configured pipeline JSON

The CLI expects an object containing a non-empty `steps` list. A deterministic
preparation pipeline can be declared as:

```json
{
  "steps": [
    {"name": "clean"},
    {
      "name": "chunk",
      "params": {
        "chunk_size": 384,
        "overlap": 48,
        "tail_policy": "emit_short"
      }
    },
    {"name": "embed"}
  ]
}
```

Supported configured steps are `clean`, `chunk`, and `embed`, in compatible
type order. The pipeline must end with `embed`, which returns `Result` values.
The `--set step.params.key=value` CLI form overlays values for matching steps;
record the resolved configuration rather than only the base JSON file.

## Retrieval configuration

The local index CLI exposes:

- backend: `bm25` or `numpy-cosine`;
- embedder: deterministic `hash16` or optional `sbert`;
- sentence-transformer model name;
- BM25 token-bucket count;
- chunk size, overlap, and tail policy;
- query `top_k`, repeatable metadata filters, and optional reranking.

`hash16` is a deterministic contract and test adapter, not a semantic model.
For `sbert`, record the model identifier and installed model dependency with
the index. Changing backend, embedder, dimension, metric, or normalization
creates a different retrieval artifact.

## HTTP configuration

`POST /v1/chunks` accepts chunk size, overlap, embedding inclusion, and source
documents. `POST /v1/index/build` accepts backend, chunk size, and overlap.
Retrieve and ask accept index identity, query, `top_k`, and metadata filters;
ask also accepts reranking policy.

HTTP indexes are held in process memory. No configuration turns that adapter
into durable storage. Persistence, authentication, request quotas, and tenancy
belong to the hosting application.

## Configuration ownership

Keep secrets and environment-specific paths outside pipeline JSON. Inject
effectful adapters as application resources rather than encoding live objects
in configuration. Persist the resolved, secret-free configuration beside
chunks, indexes, and evaluation results so a reviewer can reproduce the data
shape without acquiring the original execution environment.
