# Invariants

These are the truths maintainers should protect when refactoring ingest code.

- deterministic ingest transforms stay separate from adapter code
- domain protocols stay free of concrete embedder behavior
- retrieval helpers stay package-local instead of becoming a generic dumping ground
- pinned API schema changes are intentional and reviewed
