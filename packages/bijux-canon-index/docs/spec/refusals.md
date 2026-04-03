# What bijux-vex refuses to be

- Not a vector database: no storage SLAs, no CRUD API beyond execution ingestion.
- Not a retrieval framework: no RAG orchestration, no ranking pipelines beyond execution plans.
- Not an embedding service: no model hosting or embedding generation.
- Not a serving layer: no latency/availability guarantees, budgets are experimental not production SLAs.
- Not a benchmarking suite: comparisons exist for contract enforcement, not leaderboard results.
- Not a reasoning engine: vector execution only.

Intentionally missing abstractions:

- No schema migration helpers for embeddings
- No plug-and-play ANN plugin registry beyond declared runners
- No automatic fallback unless declared by the runner/plan
- No implicit retries on invariant/ABI violations
