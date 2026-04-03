# INVARIANTS

`bijux-canon-agent` keeps these invariants:
- pipeline execution remains auditable and trace-backed
- agent implementations do not absorb runtime persistence authority
- package boundaries stay thin around CLI, HTTP, and artifact serialization
- generated artifacts stay outside `src/`

If a change weakens auditability, boundary clarity, or artifact discipline, it should be treated as a design regression.
