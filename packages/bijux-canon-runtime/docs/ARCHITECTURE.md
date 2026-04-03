# ARCHITECTURE

`bijux-canon-runtime` is a governed execution and replay package.

Core layout:
- `src/bijux_canon_runtime/model/` owns durable runtime data models
- `src/bijux_canon_runtime/runtime/` owns execution engines and lifecycle internals
- `src/bijux_canon_runtime/application/` owns orchestration and replay coordination
- `src/bijux_canon_runtime/observability/` owns evidence capture, analysis, and storage
- `src/bijux_canon_runtime/interfaces/cli/` and `api/v1/` own operator boundaries

The architecture should keep execution authority and replay semantics inside runtime, with external transport and storage adapters clearly separated.
