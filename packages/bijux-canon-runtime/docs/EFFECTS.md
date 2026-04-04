# Effects

The runtime package is effectful by design, which makes effect clarity part of
its trust model.

## Main side effects

- reading manifests, policies, and execution inputs
- writing traces, storage rows, and schema artifacts
- opening and using runtime persistence backends
- emitting replay comparisons, failure records, and API responses

## Guardrails

- effectful behavior belongs in runtime engines, orchestration, observability, and boundaries
- pure models should remain side-effect free
- audit-relevant effects should leave durable evidence
