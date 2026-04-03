# EFFECTS

`bijux-canon-runtime` performs these important effects:
- reads flow manifests, policies, and execution inputs
- writes execution traces, storage rows, and schema artifacts
- opens runtime persistence backends such as the execution store
- emits replay comparisons, failure records, and API responses

Effectful behavior belongs in runtime, application, observability, and interfaces, not in pure model modules.
