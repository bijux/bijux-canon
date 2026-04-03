# bijux-canon-index identity (freeze-bound)

- bijux-canon-index **is** a vector execution engine with explicit contracts for determinism, nondeterminism, and replay.
- bijux-canon-index **is not** a vector database, embedding service, or retrieval framework. It records execution consequences; it does not offer serving SLAs.
- bijux-canon-index solves the problem of running and comparing deterministic vs approximate vector executions with auditable provenance. Reasoning execution is intentionally out of scope; bijux-canon-index is the vector execution engine.
- Use bijux-canon-index when you need: replayable vector experiments, explicit nondeterministic bounds, cross-backend drift detection, and compliance gates on approximation.
- Do **not** use bijux-canon-index when you need: low-latency serving, multi-tenant storage, model hosting, or generic RAG pipelines. Use a vector DB + discipline instead.
- Contract: every execution requires an execution contract, intent, budget, and session; provenance is mandatory for replay. If these feel heavy, bijux-canon-index is the wrong tool.
- Thesis: bijux-canon-index makes deterministic and approximate vector execution comparable, auditable, and replayable as contracts. Existing vector stores cannot enforce or explain determinism/approximation gaps at this level.
