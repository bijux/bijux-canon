# bijux-vex identity (freeze-bound)

- bijux-vex **is** a vector execution engine with explicit contracts for determinism, nondeterminism, and replay.
- bijux-vex **is not** a vector database, embedding service, or retrieval framework. It records execution consequences; it does not offer serving SLAs.
- bijux-vex solves the problem of running and comparing deterministic vs approximate vector executions with auditable provenance. Reasoning execution is intentionally out of scope; bijux-vex is the vector execution engine.
- Use bijux-vex when you need: replayable vector experiments, explicit nondeterministic bounds, cross-backend drift detection, and compliance gates on approximation.
- Do **not** use bijux-vex when you need: low-latency serving, multi-tenant storage, model hosting, or generic RAG pipelines. Use a vector DB + discipline instead.
- Contract: every execution requires an execution contract, intent, budget, and session; provenance is mandatory for replay. If these feel heavy, bijux-vex is the wrong tool.
- Thesis: bijux-vex makes deterministic and approximate vector execution comparable, auditable, and replayable as contracts. Existing vector stores cannot enforce or explain determinism/approximation gaps at this level.
