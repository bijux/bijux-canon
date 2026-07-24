---
title: Capability Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-22
---

# Capability Map

`bijux-canon-ingest` combines deterministic document preparation with a compact
local retrieval path and reusable execution safeguards. The capabilities share
typed records, explicit results, and configuration, but they retain distinct
ownership and evidence.

```mermaid
flowchart LR
    source["source rows and text"]
    prepare["filter, clean, chunk"]
    enrich["embed, observe, deduplicate"]
    persist["CSV / JSONL / local index"]
    retrieve["rank, answer, evaluate"]
    evidence["IDs, offsets, citations, diagnostics"]

    source --> prepare --> enrich --> persist --> retrieve --> evidence
```

## Preparation capabilities

| Capability | Primary implementation | Produced evidence | Boundary |
| --- | --- | --- | --- |
| Typed source admission | `core/types.py`, readers, strict interface models | `RawDoc` or explicit read failure | does not establish source accuracy or licensing |
| Deterministic cleaning | `processing/`, configured cleaners and rules | immutable `CleanDoc` and observations | offsets after cleaning address normalized text |
| Policy-driven filtering | predicates and safe rule evaluation | retained/rejected records and reports | caller policy, not source governance |
| Overlapping chunking | chunkers, tail policies, span validation | stable chunk index, offsets, text, and SHA-256 identity | identity changes when source, span, or text changes |
| Embedding | hash baseline and optional sentence-transformers adapter | vector plus optional `EmbeddingSpec` | hash vectors are not semantic evidence |
| Structural deduplication | document pipeline dedup stage | deterministic first occurrence by structural key | does not detect paraphrases or semantic duplicates |
| Streaming composition | `streaming/`, `fp/`, and result folds | ordered lazy values or typed errors | observations that need the full corpus materialize it |

## Retrieval and execution capabilities

| Capability | Primary implementation | Produced evidence | Boundary |
| --- | --- | --- | --- |
| Local lexical index | `retrieval/` BM25 implementation | persisted index identity, ordered scores and chunks | package-local reference path |
| Local dense index | NumPy cosine implementation | index metadata, embedding identity, ranked chunks | scores are specific to metric and model |
| Extractive answering | retrieval answer workflow | answer text and resolvable chunk citations | does not establish truth or corpus completeness |
| Offline evaluation | evaluation command and checked-in corpus | deterministic metrics and case results | measures the declared corpus, not general quality |
| Retry and circuit breaking | `safeguards/` | bounded attempts, breaker state, typed failure | activated only when the caller composes it |
| Resource and cache policy | resource, memoization, and effect primitives | lifetime, cache, and failure records | host owns distributed transactions and retention |
| CLI and HTTP adapters | `interfaces/` | stable files, responses, exit/status semantics | HTTP default index state is process-local |

## Read capability status precisely

The package contains several kinds of capability. They carry different
operational claims:

| Status | Examples | What a caller must supply or verify |
| --- | --- | --- |
| package-owned deterministic | typed admission, cleaning, filtering, chunking, structural deduplication, hash embedding | source/configuration identity and the selected pipeline contract |
| package-owned local effect | CSV/JSONL writing, MessagePack index persistence, BM25 and NumPy retrieval | approved paths, artifact custody, resource bounds and compatible stored format |
| adapter-dependent | sentence-transformer embedding, caller readers, storage/effect implementations | installed implementation, model/service identity, failure policy and environment evidence |
| composition-dependent | retries, circuit breakers, caches, observations and streaming folds | explicit caller composition; presence in the package does not activate the behavior |
| host-governed | authentication, tenant isolation, network policy, durable payload retention and distributed coordination | controls outside the package boundary |

“Supported” therefore means the selected implementation and its preconditions
were exercised. Importability alone does not prove that a model is available,
an output path is authorized, a cache is safely partitioned, or an HTTP index
will survive process restart.

## Distinguish preparation outcomes

| Outcome | Required evidence | Safe downstream interpretation |
| --- | --- | --- |
| admitted source | stable source identity and validated `RawDoc` | eligible for preparation, not yet normalized |
| prepared document | parent identity, effective cleaners/rules, `CleanDoc` identity and observations | normalized text is available under the recorded configuration |
| prepared chunk set | document identity, geometry, ordered chunks, normalized offsets and hashes | downstream retrieval may consume exactly this material |
| rejected source | source identity, failed rule/stage and typed error | no prepared artifact exists for that source |
| partial corpus | complete admitted/rejected inventory and explicit partial status | only named successful records are usable; corpus completeness is not implied |
| ranked candidate set | index/configuration/query identity, ordered scores and chunks | local retrieval result, not claim support or truth |
| extractive answer | exact cited chunks and answer projection | traceable quotation from normalized material, not source correctness |

The outcome label should survive serialization and handoff. A consumer must not
infer “prepared corpus” from the presence of one chunk or convert a rejected
record into an empty successful document.

## Capability selection

- Use the document-oriented pipeline when structural deduplication and
  materialized observations are required.
- Use the lazy pipeline when streaming composition is the principal need and
  its narrower post-processing contract is acceptable.
- Use the local retrieval commands for bounded, inspectable applications and
  reference evaluation.
- Use `bijux-canon-index` when retrieval requires backend capability
  negotiation, governed execution, or replayable vector provenance.
- Supply explicit safeguards around external readers, models, stores, and
  effects; the core pipeline does not add hidden retry or cache semantics.

The [invariants](../quality/invariants.md) define the laws behind these
capabilities, and the [known limitations](../quality/known-limitations.md)
state where their guarantees end.
