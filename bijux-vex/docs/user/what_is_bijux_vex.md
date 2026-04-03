# What Bijux-Vex Is (and Is Not)

Bijux-Vex is a **vector execution system**. It gives you a strict, auditable way to run vector search with hard determinism contracts, explicit non-determinism (ND) bounds, and first-class provenance. It is built for correctness, replay, and refusal when guarantees cannot be met.

What it solves

- Deterministic vector execution with verifiable replay.
- Explicit non-deterministic (ND) execution with bounded guarantees.
- Provenance you can use for audit, debugging, and comparison.
- Vector-store routing that is explicit, inspectable, and contract-safe.

What it intentionally refuses to do

- Implicitly choose backends, embeddings, or persistence.
- Mask non-determinism behind “best effort.”
- Provide silent fallbacks when a capability is missing.

How it differs from vector DBs

- Bijux-Vex is not a database. It does not promise CRUD semantics, query languages, or availability guarantees.
- It treats storage as a pluggable adapter and makes capability differences explicit.

How it differs from RAG frameworks

- Bijux-Vex is not an application framework. It does not manage prompt templates, retrieval pipelines, or LLM orchestration.
- It focuses on the execution contract and provenance, not end-to-end UX.

How it differs from ML pipelines

- Bijux-Vex is not a training or feature pipeline.
- It does not manage model lifecycle, training data, or inference services.

When **not** to use Bijux-Vex

- If you need a general-purpose vector database with rich filtering and schema management.
- If you want an end-to-end RAG stack or LLM framework.
- If you are fine with “probably correct” results and don’t need auditability.

If you need **contractual correctness**, **explicit ND behavior**, and **provenance you can defend**, Bijux-Vex is the right tool.
