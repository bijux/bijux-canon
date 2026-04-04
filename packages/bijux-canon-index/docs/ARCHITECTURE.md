# Architecture

The package is shaped around a strong center and replaceable edges.

## Main layers

- `core/` holds stable primitives, typed failures, and package-wide value objects
- `domain/` holds execution, provenance, drift, and replay semantics
- `application/` wires domain rules into package workflows
- `infra/` talks to vector stores, embedding systems, runners, and plugin infrastructure
- `interfaces/` and `api/v1/` expose boundary behavior
- `tooling/` supports benchmarks and operational package tooling

## Intended flow

1. A caller declares an execution request.
2. Application code validates and prepares the request.
3. Domain logic defines how the request should behave and what provenance must be preserved.
4. Infrastructure executes the request against a backend.
5. Boundary code returns results together with the right contract and provenance shape.

## Design expectations

- backend-specific behavior should not leak into stable domain semantics
- provenance should be first-class, not bolted on after the fact
- plugin loading should stay explicit and contract-driven
