# Non-deterministic reproducibility experiment

This walkthrough shows what changes and what stays bounded when running the same ND execution repeatedly.
ND behavior is **experimental**; use this to observe and audit variance.

## Setup

```bash
bijux vex ingest --doc "hi" --vector "[0.0, 0.0]"
bijux vex materialize --execution-contract non_deterministic
```

## Run the same ND execution 3 times

```bash
for i in 1 2 3; do
  bijux vex execute --artifact-id art-1 --vector "[0.0,0.0]" --top-k 1 \
    --execution-contract non_deterministic --execution-intent exploratory_search --execution-mode bounded \
    --randomness-seed $i --randomness-sources reference_ann_hnsw --randomness-bounded \
    --max-latency-ms 5 --max-memory-mb 5 --max-error 0.2
done
```

### What you should see

- Results may vary in rank/score order, but `ApproximationReport` records:
  - algorithm, version, backend
  - `randomness_sources`, `random_seed`
  - `recall_at_k`, `rank_displacement`, `distance_error`
- Provenance shows the randomness envelope and ND contract.

Sample truncated output (3 runs):

```json
{"approximation":{"algorithm":"hnswlib","rank_displacement":0.0,"recall_at_k":1.0,"random_seed":1},"results":[{"rank":1,"score":0.0,"vector_id":"vec-0"}]}
{"approximation":{"algorithm":"hnswlib","rank_displacement":0.0,"recall_at_k":1.0,"random_seed":2},"results":[{"rank":1,"score":0.0,"vector_id":"vec-0"}]}
{"approximation":{"algorithm":"hnswlib","rank_displacement":0.0,"recall_at_k":1.0,"random_seed":3},"results":[{"rank":1,"score":0.0,"vector_id":"vec-0"}]}
```

### Replay envelope

Replay of ND executions does **not** expect equality. It validates that observed divergence stays within the recorded approximation bounds; otherwise replay fails with a contract violation.
