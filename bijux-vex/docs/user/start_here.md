# Start here — bijux-vex onboarding

## What problem does bijux-vex solve?
Vector execution often hides determinism assumptions. bijux-vex makes execution contracts explicit, auditable, and replayable so you can compare deterministic (exact) and non-deterministic (ANN) runs side by side.

## When should you use it?
- You need reproducible deterministic vector execution with provenance you can replay.
- You want bounded, auditable non-deterministic execution (ANN) with explicit approximation and randomness metadata.
- You care about comparing exact vs approximate results across backends and artifacts.

## Deterministic vs non-deterministic (high level)
- Deterministic: exact search, bit-stable, replay required. No hidden randomness.
- Non-deterministic (ANN, experimental): approximate path only, bounded divergence, emits `ApproximationReport` + `RandomnessProfile`, replay is envelope-based.

## Start here path (canonical)
1) CLI flow: `ingest` → `materialize` → `execute` → `replay` → `compare`.
2) Concepts: [overview/concepts.md](../overview/concepts.md).
3) Example walkthrough: [examples/overview.md](../examples/overview.md).

## Quickstart (Workflow A)

```bash
--8<-- "docs/examples/workflows/workflow_a.sh"
```

## What to read next
1) Concepts: [overview/concepts.md](../overview/concepts.md) — mental model of execution vs storage.
2) Contracts: [spec/system_contract.md](../spec/system_contract.md) and [spec/execution_contracts.md](../spec/execution_contracts.md).
3) Examples: [examples/overview.md](../examples/overview.md) — deterministic and ANN flows.
4) API: [api/index.md](../api/index.md) and the canonical schema [api/v1/schema.yaml](https://github.com/bijux/bijux-vex/blob/main/api/v1/schema.yaml).
5) Not a vector DB: [user/not_a_vdb.md](not_a_vdb.md).
6) BYO vectors vs auto-embeddings: [user/byo_vectors_vs_embeddings.md](byo_vectors_vs_embeddings.md).
