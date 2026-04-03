
## Subsystem Non-Goals
STATUS: EXPLANATORY

Retrieval:
- Not optimized for massive corpora beyond BM25 chunking; no hybrid retrieval here.
- No automatic reranking or dense embeddings.

Reasoning:
- Not optimizing for creativity or fluency; only verifiable citations.
- No multi-model orchestration or prompt tinkering for quality.

Verification:
- Not proving factual correctness; only provenance/structure.
- Not providing partial/soft checks or probabilistic acceptance.

Execution:
- Not optimizing for throughput or low latency; determinism and auditability take priority.
- No concurrent/async execution paths that break ordering or determinism.***
