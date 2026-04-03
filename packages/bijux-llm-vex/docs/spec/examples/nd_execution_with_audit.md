# Non-deterministic execution with audit

Non-deterministic execution is **experimental** in behavior; provenance must label it accordingly.

```bash
bijux vex execute --artifact-id art-1 --vector "[0.5,0.6]" --top-k 1 \
  --execution-contract non_deterministic --execution-intent exploratory_search --execution-mode bounded \
  --randomness-seed 1 --randomness-sources reference_ann_hnsw --randomness-bounded \
  --max-latency-ms 50 --max-memory-mb 20 --max-error 0.2
```

Expected:

- RandomnessProfile captured (seed, sources, bounded flag, budget).
- DeterminismReport includes randomness sources and reproducibility bounds.
- ApproximationReport shows recall and displacement; status may be PARTIAL if budgets trigger.

Failure example:

- Missing randomness profile or budget triggers invariant failure; execution does not start.
