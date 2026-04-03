# Determinism Guide

## Deterministic Exact Pipeline

- Use `--execution-contract deterministic`.
- Use a vector store that advertises `deterministic_exact = true`.
- Provide vectors explicitly, or use embeddings with declared determinism.

## What Breaks Determinism

- ANN execution without declared randomness.
- Vector stores that cannot guarantee exact search.
- Embedding providers without determinism metadata.

## Using Refusal Messages

When the system refuses a run:

1. Read the `reason` field in the error payload.
2. Apply the `remediation` step.
3. Retry with explicit randomness if using ANN.
