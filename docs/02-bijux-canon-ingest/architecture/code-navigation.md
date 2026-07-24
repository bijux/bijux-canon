---
title: Code Navigation
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-22
---

# Code Navigation

The fastest route through ingest is to follow the record being transformed.
Start with its immutable type, move through the owning stage, then inspect the
application or interface that composes the stage.

```mermaid
flowchart TD
    question{"What changed?"}
    shape["record shape or identity"]
    transform["cleaning, chunking, embedding, dedup"]
    flow["pipeline or streaming order"]
    retrieve["index, ranking, answer, evaluation"]
    edge["CLI, HTTP, files, configuration"]
    resilience["retry, breaker, cache, resources"]

    question --> shape
    question --> transform
    question --> flow
    question --> retrieve
    question --> edge
    question --> resilience
```

## Navigate by concern

| Concern | Begin in | Continue in | Evidence |
| --- | --- | --- | --- |
| document, chunk, span, or embedding shape | `src/bijux_canon_ingest/core/` | `interfaces/serialization/` and schemas | unit tests for core types and public API |
| filtering, cleaning, chunking, or dedup | `src/bijux_canon_ingest/processing/` | `application/` for stage assembly | processing and application tests |
| lazy values, fan-in, fan-out, or backpressure | `streaming/`, `fp/`, `result/` | scheduling/effect code used by the pipeline | streaming and property tests |
| embedding choice or vector validation | processing embedder boundary and `retrieval/` | optional integration adapters | embedder-factory and retrieval tests |
| local index, ranking, citations, or evaluation | `retrieval/` | retrieval CLI commands and persisted formats | retrieval unit tests and `tests/e2e/` |
| retry, circuit breaker, memoization, or lifetime | `safeguards/` | application boundary that opts into the policy | focused safeguard tests |
| command behavior | `interfaces/cli/` and CLI entrypoint | configuration and application workflows | CLI smoke and evaluation tests |
| HTTP behavior | HTTP interface models and routes | application and retrieval stores | interface/contract tests and tracked schema |
| optional provider behavior | integration and infrastructure adapters | dependency extras in `pyproject.toml` | focused adapter tests, never default proof |

Paths in this table are relative to
`packages/bijux-canon-ingest/src/bijux_canon_ingest/` unless stated otherwise.

## Follow a document

1. Read the type and identity rules in `core/types.py`.
2. Locate the stage implementation in `processing/`.
3. Find its configured composition in `application/`.
4. Follow serialization or persistence through `interfaces/` and `retrieval/`.
5. Confirm the owning unit test before using an end-to-end test to validate the
   cross-boundary path.

## Debug from the observed artifact backward

| Symptom | Inspect first | Then follow | Evidence that closes the diagnosis |
| --- | --- | --- | --- |
| source is missing from output | accepted/rejected inventory and typed result | reader, filters, rule evaluation and application partition | stable source identity plus exact rejection/stage record |
| normalized text changed | `CleanDoc` and effective cleaner configuration | `processing` cleaner order and core identity | before/after document fixture and observation sequence |
| chunk text is correct but offsets are wrong | chunk parent, normalized text and span validation | chunk geometry/tail policy and materialization | normalized-text slice equals chunk text at recorded offsets |
| embedding dimensions or identity drift | chunk and `EmbeddingSpec` | embedder factory, adapter/model and vector validation | model/configuration identity plus repeated vector fixture |
| duplicate survives or valid record disappears | structural key and first-occurrence order | dedup stage and pipeline selection | full input/output order and key comparison |
| persisted local index cannot load | artifact envelope, backend and fingerprint | retrieval codec, MessagePack schema and version handling | old/new round trip or explicit incompatible/corrupt refusal |
| citation points to unexpected text | candidate chunk identity and normalized span | ranking, citation assembly and source handoff | candidate-to-chunk-to-parent join with exact normalized bytes |
| HTTP and CLI disagree | strict boundary model and serialized application result | interface translation after the shared use case | same input/configuration produces equivalent typed disposition |
| retry hides a deterministic defect | attempt classification and breaker state | safeguard composition around the effectful adapter | first failure, retry decisions and final result remain visible |

Start with the artifact the caller actually observed. Do not jump directly to
an adapter stack trace: the nearest durable identity usually reveals whether
the defect entered during parsing, transformation, orchestration, retrieval or
translation.

## Place a change at the owning layer

| Desired change | Primary location | Required neighboring evidence |
| --- | --- | --- |
| new stable source or chunk field | `core` model/identity contract | serialization, public schema and compatibility fixtures |
| new cleaner, filter or chunking rule | `processing` | invariant/property cases and configured application composition |
| new complete ingest workflow | `application` | stage-level evidence plus CLI/HTTP use-case coverage as applicable |
| new local index codec or ranking behavior | `retrieval` | artifact migration/refusal, ranking and citation evidence |
| new external model/store implementation | `infra` or `integrations` | protocol conformance, failure classification and dependency identity |
| new command or route | `interfaces` | shared application behavior, boundary schema and error/status mapping |

If the same semantic rule appears in more than one interface, it belongs below
the interfaces. If adapter-specific behavior changes a core identity, make
that influence an explicit configuration or contract input.

## Public boundary landmarks

| Landmark | Why it matters |
| --- | --- |
| `_package_api.py` | curated package-root exports and public composition surface |
| CLI entrypoint and `typer_argv.py` | dispatch between document-pipeline and retrieval command families |
| `interfaces/` | transport models, serialization, and failure translation |
| package `pyproject.toml` | console entrypoint and optional dependency groups |
| `tests/e2e/test_cli_smoke.py` | file-to-command boundary |
| `tests/e2e/test_eval_suite.py` | persisted retrieval evaluation path |
| `tests/e2e/test_rag_truthfulness_gate.py` | citation and answer-quality acceptance boundary |

When a behavior crosses several rows, place the invariant at the lowest owning
layer and keep interfaces responsible only for translation. This preserves a
short path from failure to cause.
