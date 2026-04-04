# Effects

This package touches external systems directly, so its effects need to stay
easy to trace.

## Main side effects

- connecting to vector stores and embedding providers
- reading and writing backend-managed state through adapters
- loading plugins through declared entrypoints
- emitting schemas, benchmark outputs, and provenance-bearing artifacts

## Guardrails

- effectful code should live in adapters and boundary workflows
- stable core and domain models should remain side-effect free
- backend capability reporting should be truthful, even when it is inconvenient
