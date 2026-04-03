# Why vector execution ≠ vector storage

bijux-vex is a vector execution engine. It treats every query as an explicit execution with a contract, an intent, and a surfaced randomness profile. Storing vectors is necessary but insufficient; the value is in how executions are planned, run, compared, and replayed.

## Why determinism matters
- Deterministic executions (DETERMINISTIC) must replay exactly. bijux-vex refuses to run them through approximate paths and fingerprints every execution.
- Non-deterministic executions (NON_DETERMINISTIC) declare their loss surface up front: randomness sources, replay bounds, and provenance flags.

## Why approximation must be explicit
- ANN is only allowed when the execution intent justifies it (exploratory search, production retrieval with budgets).
- RandomnessSurface captures the sources of non-determinism so divergence is declared, not hidden.

## Why existing VDBs conflate concerns
- Most vector databases merge storage and execution, hiding algorithm choice and randomness behind “query” APIs.
- They rarely expose execution lineage, making replay and cross-backend comparison brittle.

## How bijux-vex fits the ecosystem
- bijux-vex focuses on vector execution with explicit determinism semantics; reasoning and RAG concerns live elsewhere. Execution traces, contracts, and intents remain first-class here for vector workloads.
- VectorExecution is the unit of meaning here: it records the request, contract, backend, algorithm, parameters, and randomness surface. Artifacts reference executions by hash, keeping lineage auditable.

Use bijux-vex when you need to compare exact vs approximate runs, measure divergence, and keep replayability honest. Don’t use it as a generic datastore or a serving tier—it’s an execution lab, not a database.
