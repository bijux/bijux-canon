# Mental Model

`bijux-canon-index` is an execution package, not a general vector database.

The package accepts declared execution intent and contract, runs the request against a stored artifact, and returns results with enough provenance to explain, compare, and replay the outcome later.

Keep these boundaries in mind:
- `core` defines durable execution types, contracts, and invariants.
- `domain` defines execution semantics such as planning, scoring, replay, and drift handling.
- `application` wires those rules into package-facing workflows.
- `infra` owns storage, ANN runners, embeddings, and plugin loading.
- `interfaces` owns CLI and HTTP request shaping.

The main question this package answers is not only "what were the nearest vectors?" but also "under which contract, with which artifact, and with which replay guarantees did we produce them?"
