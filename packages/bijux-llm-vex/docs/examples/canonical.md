# Canonical vector execution pipeline

This is the single example to understand bijux-vex:

1. ingest a small corpus (document + vector)
2. materialize an execution artifact (deterministic)
3. execute deterministically
4. execute non-deterministically with randomness declared
5. compare the two executions
6. explain a result

Everything else in bijux-vex is this pipeline with different knobs.
