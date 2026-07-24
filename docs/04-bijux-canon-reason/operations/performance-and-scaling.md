---
title: Performance and Scaling
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-21
---

# Performance and Scaling

`bijux-canon-reason` turns a problem specification into a content-addressed
plan, executes that plan through a declared runtime, verifies the resulting
trace, and writes a replayable run bundle. Performance therefore includes more
than model or tool latency: retrieval, evidence capture, canonical
serialization, verification, hashing, and replay are all part of the cost of a
trustworthy result.

```mermaid
flowchart LR
    spec[ProblemSpec] --> plan[Plan DAG]
    plan --> tools[Runtime and tools]
    tools --> evidence[Evidence and claims]
    evidence --> trace[Canonical trace]
    trace --> verify[Verification]
    verify --> bundle[Manifested run bundle]
    bundle --> replay[Frozen replay]
```

An optimization is acceptable only when the same evidence, linkage,
verification, and replay guarantees remain observable. A shorter run that
drops exact support bytes or changes event ordering is a different execution,
not a faster equivalent execution.

## Where Time and Space Go

| Cost centre | Primary scale variable | What to measure |
| --- | --- | --- |
| planning | plan nodes and dependency edges | planning latency, plan size, stable plan ID |
| tool execution | calls, provider latency, returned bytes | per-tool latency, failures, result size |
| local retrieval | corpus bytes, documents, chunks, queries | index build/load time, query latency, selected supports |
| evidence capture | evidence items and exact support spans | evidence bytes, support count, rejected supports |
| trace construction | events and serialized payload size | event count, JSONL bytes, canonicalization time |
| verification | events, claims, supports, invariant checks | verification latency, checks and failures |
| packaging | retained files and their bytes | write time, digest time, run-directory size |
| replay | original events and recorded tool results | replay latency, fingerprint equality, diff size |

The trace grows with every `step_started`, `step_finished`, `tool_called`,
`tool_returned`, `evidence_registered`, and `claim_emitted` event. Tool results
and evidence can dominate storage even when the plan is small. Measure event
count and serialized bytes together; neither alone explains the cost.

## Retrieval Geometry

The local BM25 runtime can pin a JSONL corpus and its derived chunks inside the
run bundle. Three inputs dominate retrieval cost:

- corpus bytes and document count determine ingestion work;
- `chunk_chars` and `overlap_chars` determine the number of chunks and how
  much source text is duplicated;
- query count and candidate count determine ranking and evidence-selection
  work.

More overlap can preserve context across chunk boundaries, but increases index
size, ranking work, and provenance storage. Smaller chunks can improve the
precision of a support span while multiplying candidates. Tune chunk geometry
against retrieval quality and verified support coverage, not latency alone.

Use the runtime limits for predictable failure instead of allowing an
unbounded run:

| Limit | Protected resource |
| --- | --- |
| `RAR_RETRIEVAL_CORPUS_MAX_BYTES` | bytes read from a local corpus |
| `max_docs` | documents admitted to the retrieval index |
| `max_chunks` | chunks admitted after segmentation |
| `RAR_RUN_DISK_QUOTA_BYTES` | bytes retained in the run directory |

An existing BM25 index is reusable only when its corpus identity, chunking,
scoring configuration, and limits match the requested runtime. Reusing an
index across a configuration mismatch saves time by changing the experiment.

## Concurrency and Ordering

Independent tool calls may be executed concurrently by a custom runtime, but
the canonical trace is ordered evidence. Concurrency must preserve stable
event indices, call/result pairing, step boundaries, evidence IDs, and claim
links. If completion timing is allowed to choose trace order, the resulting
fingerprint can vary between otherwise identical runs.

Bound concurrency at the runtime or provider boundary. Consider provider rate
limits, response size, and local serialization pressure together; raising
parallelism can move the bottleneck from tool latency to memory, trace writes,
or downstream throttling.

## Resource Budgets

The run writer supports disk, elapsed-time, and CPU-time budgets. The elapsed
and CPU budgets are checked after execution; they report an over-budget run but
do not pre-empt a blocking provider call. Use provider timeouts and an external
supervisor when hard cancellation is required.

Disk use includes the core bundle, pinned provenance, retrieval indexes, and
later derived files such as standalone verification and replay traces. Exact
support bytes and their hashes are part of the evidence contract and must not
be removed merely to reduce storage. Control growth earlier by bounding the
corpus, plan, tool results, and evidence set.

## A Comparable Benchmark Record

Record enough context to explain both speed and scientific behaviour:

1. retain the exact `ProblemSpec`, plan ID, preset, seed, and runtime
   descriptor;
2. identify corpus and index fingerprints, chunk geometry, scoring settings,
   and all resource limits;
3. separate planning, index build or load, query, tool, verification,
   serialization, digest, and replay timings;
4. report plan nodes, tool calls, evidence items, claims, trace events, and run
   bytes;
5. record cache state, provider versions, package version, machine class, and
   concurrency;
6. pair latency and throughput with verification failures, evidence coverage,
   and replay fingerprint equality.

Warm-index and cold-index measurements answer different questions and should
be reported separately. External provider latency should also be separated
from local reasoning overhead.

## Scaling Beyond One Process

Run directories are the durable unit of evidence. The HTTP service's local
state and file-backed bundles are suitable for a single deployment boundary;
they are not a distributed scheduler or shared transaction system. Horizontal
service scaling requires external ownership for request routing, run IDs,
shared artifact storage, authentication, isolation, and retry coordination.

Keep each run immutable after completion and scale independent runs rather
than splitting one trace across uncoordinated writers. This retains a single
authority for event order, verification, and the manifest.

## Operational Decisions

- If retrieval dominates, bound and profile corpus preparation before changing
  reasoning logic.
- If providers dominate, inspect call count, response size, concurrency, and
  retry policy before changing the trace contract.
- If verification or hashing dominates, measure event and artifact growth;
  do not bypass either integrity layer.
- If replay is slow, compare it with original local execution time and inspect
  recorded result size. Replay deliberately re-executes the plan against frozen
  results.
- If run directories grow unexpectedly, attribute bytes to core artifacts,
  provenance, indexes, verification output, and replay output separately.

See [Configuration Surface](../interfaces/configuration-surface.md) for limits,
[Artifact Contracts](../interfaces/artifact-contracts.md) for retained state,
and [Observability and Diagnostics](observability-and-diagnostics.md) for the
evidence used to investigate a slow or divergent run.
