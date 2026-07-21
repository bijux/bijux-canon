---
title: Test Strategy
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Test Strategy

The ingest test suite follows the data from value construction through
streaming execution and public boundaries. Each layer answers a different
question; no single end-to-end example substitutes for the domain laws below
it.

## Evidence layers

| Test family | Principal claim |
| --- | --- |
| `tests/unit/domain/` | effect plans, retries, scheduling, backpressure, idempotency, and session behavior preserve their laws |
| `tests/unit/fp/` and `tests/unit/result/` | composition, validation, state, result folds, and streams obey value/error semantics |
| `tests/unit/processing/` and `tests/unit/core/` | cleaning, spans, tail policies, embedding, rules, and structural dedup produce stable results |
| `tests/unit/streaming/` | fan-in, fan-out, contiguity, sampling, and lazy dedup retain ordering and termination behavior |
| `tests/unit/application/` | configured pipelines connect readers, stages, observations, indexing, and services correctly |
| `tests/unit/retrieval/` | embedder selection, text analysis, and reference index APIs respect their declared contracts |
| `tests/unit/safeguards/` | retry bounds, breaker modes, memoization, reports, and resource closure remain explicit |
| `tests/e2e/` | CLI flows, saved indexes, deterministic evaluation, and retrieval/answer paths work across boundaries |
| `tests/invariants/` | documentation, source labels, repository shape, and generated-file hygiene remain intact |

## High-risk change matrix

| Change | Focused evidence |
| --- | --- |
| chunk identity or offsets | core type, chunking, processing, and serialization tests |
| normalization or filtering | processing-stage and rules tests, then application pipeline tests |
| lazy iteration or concurrency | streaming plus async scheduling/backpressure/property tests |
| embedding implementation | embedder-factory and retrieval tests; deterministic evaluation for the CI profile |
| deduplication key or order | core rules/dedup and streaming tests |
| retry, breaker, cache, or resource lifetime | corresponding safeguard tests plus the affected application boundary |
| CLI or HTTP model | focused interface tests, checked-in schema drift, and CLI smoke test |
| retrieval-quality baseline | offline evaluation corpus and truthfulness gate; never unit tests alone |

## Property and law tests

The package uses generated inputs where correctness is algebraic or
schedule-sensitive. These tests cover such properties as bounded retry,
associative composition, stable ordering, idempotent execution, and async plan
equivalence across input ranges that would be weakly represented by a few
fixtures.

Property tests do not prove an external embedder's semantic quality. The
offline evaluation suite addresses reference retrieval behavior separately,
using a deterministic CI profile and checked-in corpus.

## Boundary evidence

Public interface testing has three distinct responsibilities:

1. strict models reject malformed or extra data and serialize stable envelopes;
2. CLI and HTTP adapters map domain success and error results without changing
   their meaning;
3. end-to-end runs prove that configuration, document input, index persistence,
   retrieval, and answer generation connect correctly.

Tests use the hash embedder for deterministic proof unless the test is
explicitly about an optional model integration. A green hash-based test says
nothing about semantic fitness; quality claims must come from the evaluation
corpus and the production model's own recorded evidence.

## Regression standard

A defect fix should add the narrowest failing test at the owning layer before
adding broader coverage. Broader checks are justified when the defect crossed
a public interface, persistence format, or package boundary. This keeps a
future failure close to its cause and preserves the distinction between
transformation correctness and retrieval quality.
