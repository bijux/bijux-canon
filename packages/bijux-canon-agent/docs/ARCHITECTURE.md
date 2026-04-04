# Architecture

The package is organized around a simple shape: thin boundaries, a durable
pipeline core, and role-local behavior that stays close to the role it serves.

## Main layers

- `agents/` holds concrete roles and helpers that are meaningful only for those roles
- `pipeline/` owns lifecycle coordination, step sequencing, termination, and result shaping
- `application/` composes pipeline pieces into package-level workflows
- `interfaces/cli/` and `api/v1/` expose operator-facing boundaries
- `traces/`, `observability/`, and `config/` support traceability, telemetry, and configuration loading

## Intended flow

1. A CLI or HTTP boundary accepts a request and validates package-facing input.
2. The application layer turns that request into a pipeline invocation.
3. The pipeline coordinates roles, produces outputs, and records traceable artifacts.
4. Boundary code serializes the outcome without absorbing pipeline business logic.

## Design expectations

- boundary modules should stay thin and reversible
- pipeline code should explain execution clearly enough that traces make sense later
- role-specific logic should not be hidden inside generic orchestration helpers
- observability should describe execution, not secretly control it
