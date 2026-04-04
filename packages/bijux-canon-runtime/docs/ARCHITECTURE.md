# Architecture

The runtime package is easiest to understand when you separate durable models,
execution engines, orchestration, and evidence handling.

## Main layers

- `model/` defines durable runtime data models
- `runtime/` contains execution engines and lifecycle internals
- `application/` coordinates planning, execution, replay, and persistence workflows
- `observability/` captures, stores, and analyzes evidence about execution
- `interfaces/` and `api/v1/` expose operator-facing boundaries

## Intended flow

1. A boundary receives a manifest, command, or replay request.
2. Application code resolves the request into a runtime workflow.
3. Runtime engines execute the flow in the chosen mode.
4. Observability code records the evidence needed for audit and replay.
5. Boundaries render the outcome without absorbing runtime authority into transport code.
