---
title: Configuration Surface
audience: mixed
type: reference
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-07-21
---

# Configuration Surface

Index configuration has two layers: environment configuration selects durable
resources, while every execution request declares its scientific and
operational contract. Keep them separate so backend deployment does not
silently decide acceptable loss.

## Resource configuration

TOML and YAML configuration accept three sections:

```yaml
vector_store:
  backend: sqlite
  uri: artifacts/bijux-canon-index/state.sqlite

embeddings:
  provider: local
  model: controlled-model-id
  cache:
    backend: filesystem
    uri: artifacts/bijux-canon-index/embedding-cache

resource_limits:
  max_vectors_per_ingest: 50000
  max_k: 100
  max_query_size: 8192
  max_execution_time_ms: 30000
```

`--config` loads `.toml`, `.tml`, `.yaml`, or `.yml`; YAML uses safe loading.
CLI vector-store, embedding, and cache options override the corresponding
resource selection. Record the resolved configuration, not only the file.

Environment variables can select the package state backend and path, read-only
mode, authorization mode, and ANN circuit thresholds. Canonical variables use
the `BIJUX_CANON_INDEX_` prefix; legacy `BIJUX_VEX_` names remain compatibility
inputs. Prefer canonical names for all new deployments.

## Execution declaration

| Declaration | Values or fields | Effect |
| --- | --- | --- |
| intent | `exact_validation`, `reproducible_research`, `exploratory_search`, `production_retrieval` | Records why the execution and loss posture are acceptable |
| contract | `deterministic`, `non_deterministic` | Selects exact or approximate semantics |
| mode | `strict`, `bounded`, `exploratory` | Controls refusal and tolerance |
| budget | latency, memory, error, vectors, distance computations, ANN probes | Bounds execution before results are accepted |
| request | vector or text, artifact identity, `top_k` | Defines the requested operation |
| randomness | seed, sources, bounded flag, non-replayable declaration | Defines whether approximate work can be reconstructed |

Deterministic execution requires strict mode. Non-deterministic execution
requires bounded or exploratory mode and a budget. Supplying ANN configuration
to a deterministic request is invalid.

## ANN configuration

Approximate execution can declare profile, target recall, latency budget,
witness rate and mode, candidate pool, diversity, normalization, low-signal
thresholds, adaptive `k`, on-demand or incremental index construction, memory
and candidate caps, two-stage reranking, and HNSW parameters.

These values are part of provenance. A changed `ef_search`, metric, candidate
pool, normalization rule, or index build is a changed execution, even when the
same query and backend name are used.

## Precedence and persistence

Use this precedence explicitly:

1. package defaults establish local behavior;
2. environment selects deployment resources;
3. TOML or YAML supplies application configuration;
4. CLI or HTTP request fields select one operation.

Do not put credentials in a vector-store URI that will enter configuration,
logs, or provenance. Backend lineage exposes a redacted URI; the secret itself
belongs in the adapter's credential mechanism or process secret store.

Run records default to `artifacts/bijux-canon-index/runs` and can be relocated
with `BIJUX_CANON_INDEX_RUN_DIR`. Keep the configuration, artifact fingerprint,
execution plan, and run record under the same retention policy.
