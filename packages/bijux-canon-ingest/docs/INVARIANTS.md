# INVARIANTS

`bijux-canon-ingest` keeps these invariants:
- deterministic ingest transforms stay separate from adapter code
- domain protocols stay free of concrete embedder behavior
- retrieval helpers stay package-local and do not absorb unrelated app logic
- pinned API schema changes are intentional and reviewed
