# ANN execution example

ANN execution is **experimental** until graduation criteria are met.

```bash
bijux vex execute --artifact-id art-1 --vector "[0.3,0.4]" --top-k 1 \
  --execution-contract non_deterministic --execution-intent exploratory_search --execution-mode bounded \
  --randomness-seed 1 --randomness-sources reference_ann_hnsw --randomness-bounded \
  --max-latency-ms 10 --max-memory-mb 10 --max-error 0.2
```

Expected:

- ANN algorithm selected, randomness sources recorded
- ApproximationReport persisted with recall/rank displacement
- DeterminismReport present with reproducibility bounds

Failure example:

- Missing budget or randomness profile ⇒ invariant failure before execution.
