---
title: Configuration Surface
audience: mixed
type: reference
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-21
---

# Configuration Surface

Reasoning behavior is configured at four boundaries: the problem
specification, the execution policy, the command invocation, and the process
environment. Keep all four with a run when reproducibility matters.

## Problem specification

The JSON `ProblemSpec` is the durable input contract. Its `constraints` object
also selects retrieval and evidence behavior:

| Constraint | Default | Effect |
| --- | ---: | --- |
| `needs_retrieval` | `false` | use the local BM25 runtime when a corpus is available |
| `corpus_path` | packaged small corpus when retrieval is requested and the fixture is available | JSONL corpus used by local retrieval |
| `chunk_chars` | `800` | target chunk size |
| `overlap_chars` | `120` | character overlap between adjacent chunks |
| `bm25_k1` | `1.2` | BM25 term-frequency saturation |
| `bm25_b` | `0.75` | BM25 length normalization |
| `min_supports_per_claim` | `2` | minimum evidence references for a derived claim; values are clamped to at least one |
| `max_citations` | minimum support count | maximum citations selected for a derivation; never lower than the minimum support count |

For example:

```json
{
  "description": "Identify the evidence-supported conclusion",
  "constraints": {
    "needs_retrieval": true,
    "corpus_path": "data/corpus.jsonl",
    "chunk_chars": 800,
    "overlap_chars": 120,
    "bm25_k1": 1.2,
    "bm25_b": 0.75,
    "min_supports_per_claim": 2,
    "max_citations": 4
  }
}
```

Relative corpus paths are resolved from the process working directory. Use a
pinned corpus file and record its digest rather than depending on mutable input.

## Run and verification controls

The CLI run surface accepts the specification path, preset name, integer seed,
artifact root, and `--fail-on-verify`. The content-derived run identifier
includes the specification identifier, preset, seed, and runtime fingerprint;
changing any of them intentionally creates a different run identity.

The Python executor additionally accepts `ExecutionPolicy`. Its defaults are
`fail_fast=True` and `min_supports_per_claim=2`; a specification constraint can
override the latter. Verification accepts `strict`, `audit`, or `permissive`
policy mode. Replay has its own `--fail-on-diff` gate.

## Environment controls

| Variable | Default | Meaning |
| --- | ---: | --- |
| `RAR_RETRIEVAL_CORPUS_MAX_BYTES` | `0` | corpus byte ceiling; zero disables the ceiling |
| `RAR_RUN_DISK_QUOTA_BYTES` | `0` | run-directory disk ceiling; zero disables it |
| `RAR_RUN_TIME_BUDGET_SEC` | `0` | elapsed-time budget checked after execution; zero disables it |
| `RAR_RUN_CPU_BUDGET_SEC` | `0` | CPU-time budget checked after execution; zero disables it |
| `RAR_API_TOKEN` | unset | exact token required in `x-api-token` when configured |
| `RAR_API_RATE_LIMIT` | `0` | process-local request limit; zero disables rate limiting |

The resource budgets are read when the run-artifact module is imported. Set
them before starting the process. Time and CPU budgets are post-run checks, not
preemptive cancellation controls.

The HTTP application accepts an artifact root when it is created; otherwise it
uses `artifacts/bijux-canon-reason`. That root owns both run artifacts and the
SQLite item store.
