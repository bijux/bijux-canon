# BOUNDARIES

`bijux-canon-runtime` owns manifest execution, replay, execution evidence capture, and runtime persistence rules.

It does own:
- runtime authority and replay semantics
- trace capture and execution-store behavior
- operator CLI and API boundaries for runtime flows

It does not own:
- agent composition policy from `bijux-canon-agent`
- ingest and vector index package semantics
- repository tooling from `bijux-canon-dev`
