# Architecture Diagram & Walkthrough

## High-level diagram

```
request
  └─> plan
        ├─ deterministic path
        │    ├─ exact execution
        │    └─ provenance
        └─ ND path
             ├─ runner selection
             ├─ ANN execution
             ├─ witness / quality metrics
             └─ provenance

storage & adapters
  ├─ memory / sqlite
  ├─ faiss
  └─ qdrant

embeddings
  ├─ explicit provider
  └─ explicit cache
```

## Walkthrough

1. **Request**
A CLI or API request is validated and normalized. All implicit behavior is refused. Optional components must be explicitly declared.

2. **Plan**
The system produces an execution plan that captures mode (deterministic or ND), budgets, runner selection, and adapter configuration.

3. **Execution**
- Deterministic path uses exact search and rejects any non-deterministic component.
- ND path selects a runner, executes ANN, and may perform witness verification or quality measurement.

4. **Postprocess**
Results are ordered by a canonical contract. ND postprocess may re-rank or refuse based on quality policy.

5. **Provenance**
Every execution emits a provenance artifact describing inputs, decisions, randomness, and bounds. This is the basis for replay and audit.

This model ensures users always understand what happened, why it happened, and what the system refused to do.
