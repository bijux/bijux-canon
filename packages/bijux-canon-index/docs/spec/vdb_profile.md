# Vector Store Profile

Vector-store integrations in `bijux-canon-index` must describe behavior through a stable profile rather than ad-hoc backend claims.

Each backend profile should state:
- whether exact queries are deterministic
- whether ANN queries are supported
- whether delete and filtering are supported
- what consistency semantics the backend exposes
- which backend version and plugin source produced the capability report

The package treats vector stores as execution dependencies, not opaque infrastructure. Their profile is part of provenance, capability reporting, and replay reasoning.

When adding a backend, prefer declaring the narrowest truthful profile first and broadening later only when the implementation and tests prove it.
