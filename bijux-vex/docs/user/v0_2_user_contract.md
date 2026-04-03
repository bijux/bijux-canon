# v0.2 User Contract (Human)

This is the plain‑language contract for v0.2. It is not legal. It is a promise about behavior.

Guaranteed

- Deterministic execution is exact and replayable.
- Canonical ordering rules apply to deterministic results.
- Provenance is emitted for every execution.
- Refusals are explicit and structured.

Bounded

- Non‑Deterministic (ND) execution is approximate but audited with metrics.
- ND replay is possible only within declared bounds.
- Performance depends on the selected backend and budgets.

Best‑effort

- Latency targets and throughput goals.
- Optional backend optimizations.

Out of scope

- Acting as a vector database.
- Managing LLM orchestration or RAG pipelines.
- Silent fallbacks or implicit behavior.
