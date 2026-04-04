# Architecture

The package works best when planning, execution, reasoning, and verification
are related but still clearly separable.

## Main areas

- `planning/` decides how reasoning work should be shaped
- `reasoning/` defines claim and reasoning semantics
- `execution/` runs reasoning steps and handles local tool dispatch
- `verification/` evaluates outcomes against package-local rules
- `retrieval/` and `evaluation/` support evidence use and assessment
- `interfaces/` and `api/v1/` expose boundary behavior

## Intended flow

1. A request enters through a package boundary.
2. Planning code decides how the reasoning workflow should proceed.
3. Execution code runs the steps.
4. Reasoning code produces structured outputs.
5. Verification code checks those outputs before the boundary returns them.

Boundary code should stay thin enough that the core reasoning story remains easy
to test and easy to explain.
