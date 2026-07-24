---
title: Data Contracts
audience: mixed
type: reference
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-07-21
---

# Data Contracts

Index separates corpus data, execution policy, and result evidence. That
separation is deliberate: a vector says what can be searched, an execution
request says what guarantees are required, and a result says what a particular
run returned.

```mermaid
flowchart LR
    Document --> Chunk --> Vector
    Vector --> Artifact[ExecutionArtifact]
    Request[ExecutionRequest] --> Run[VectorExecution]
    Artifact --> Run
    Run --> Result
    Result --> Explain[explanation and replay]
```

## Corpus Primitives

| Type | Stable meaning |
| --- | --- |
| `Document` | source identity, text, optional source and version |
| `Chunk` | document-owned text span with ordinal and optional offsets |
| `Vector` | vector identity, chunk identity, values, declared dimension, model, metadata |
| `ModelSpec` | model identity, dimension, vendor, and version |

`Vector` freezes values as a tuple, requires a positive dimension, and rejects
a value count that differs from the declared dimension. Metadata is normalized
to string pairs. These checks make dimension and identity failures visible
before backend execution.

## Execution Request

`ExecutionRequest` structurally carries a request ID, optional query text,
optional vector, `top_k`, an `ExecutionContract`, and an `ExecutionIntent`. The
core constructor enforces contract, intent, mode, and non-deterministic policy
relationships. It does not by itself require query material or a positive
`top_k`; the HTTP validators enforce those boundary rules. Code constructing
core requests directly must validate the operation-specific fields before
execution.

The contract and mode must agree:

- deterministic execution requires `strict` mode and forbids non-deterministic
  settings;
- non-deterministic execution requires `bounded` or `exploratory` mode and an
  explicit budget; and
- ANN quality settings validate ranges, candidate counts, witness policy,
  memory limits, and distance space before planning.

`ExecutionBudget` makes latency, memory, error, vector-count, distance, and ANN
probe limits part of the request. `NDSettings` makes approximation policy part
of the request. Neither should be reconstructed from logs after execution.

## Identity Through the Query Path

The identifiers are related by explicit joins, not by a shared string:

| Identity | Allocated by | Resolves to |
| --- | --- | --- |
| `document_id` | corpus producer | source document |
| `chunk_id` | chunk producer | span owned by a document |
| `vector_id` | embedding producer | vector owned by a chunk |
| `artifact_id` | materialization caller | corpus, index configuration, and execution contract |
| `request_id` | query caller | ranked `Result` rows through `Result.request_id` |
| `execution_id` | execution runtime | plan, signature, result set, and persisted run |
| correlation ID | interface lifecycle | request-facing tracking value and run-directory prefix |

An execute response exposes ordered `vector_id` values, the correlation ID,
and the runtime `execution_id`. The on-disk run ID appends a generated suffix to
the correlation ID and is not returned as a separate field. The response does
not expose document or chunk identity, scores, or rank fields. Resolve those
through explanation and retained ledger state; never parse one identifier to
manufacture another.

## Boundary Payloads

HTTP payloads use strict Pydantic models rather than accepting core dataclasses
directly. Unknown fields are rejected. Important request rules include:

- ingest accepts either vectors aligned one-for-one with documents or an
  embedding model;
- execute requires query text or a vector and requires `top_k > 0`;
- non-deterministic execute requests must declare valid randomness and budget
  policy; and
- artifact materialization accepts only `exact` or `ann` as an index mode.

Responses preserve ordered vector identifiers and the identity needed to locate
their audit context. Execute, explain, and replay responses carry the execution
contract, status, replayability, and execution ID. Replay additionally returns
original and replay fingerprints, mismatch details, and non-deterministic
sources.

## Core Result Versus API Result

The core `Result` is a scored retrieval row with document, chunk, vector,
artifact, score, and rank. `ExecuteResponse.results` is an ordered list of
vector IDs designed for the HTTP boundary. Consumers that require scores or
lineage should request explanation evidence instead of assuming the compact API
response contains the full internal row.

Changing identity meaning, dimension validation, execution-mode rules, score
semantics, ordering, or replay fields is compatibility-sensitive. See
[Artifact Contracts](artifact-contracts.md) for persisted execution evidence.
