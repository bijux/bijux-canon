# Effects

This package is effectful in real ways, and the docs should make those effects
easy to reason about.

## Main side effects

- reading prompts, configuration, and workflow input assets
- calling model-provider adapters through `llm/`
- emitting traces, result artifacts, and logs
- publishing telemetry through `observability/`

## Guardrails

- effectful code should stay close to adapters and boundaries
- pure execution decisions should remain understandable without external I/O
- traces must preserve enough information to explain the effectful parts of a run
- hidden ambient behavior is a design smell; make dependencies explicit
