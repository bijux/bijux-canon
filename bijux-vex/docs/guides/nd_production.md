# ND In Production

This guide shows how to run non-deterministic (ND) execution safely and intentionally.

## Choose A Profile

Use an explicit profile to set baseline quality:

```bash
bijux vex execute \
  --execution-contract non_deterministic \
  --execution-intent exploratory_search \
  --execution-mode bounded \
  --randomness-seed 42 \
  --randomness-sources ann_index \
  --nd-profile balanced \
  --vector '[0.1,0.2]' \
  --top-k 5
```

Profiles:
`fast` trades recall for latency,
`balanced` is the default tradeoff,
`accurate` prioritizes recall.

## Set A Recall Target

```bash
--nd-target-recall 0.95
```

If the backend cannot honor the target, the request is refused with a remediation hint.

## Enforce A Latency Budget

```bash
--nd-latency-budget-ms 20
```

When latency exceeds the budget, ND may degrade in a declared ladder:
reduce `k`, switch profile, or refuse.

## Tune Profiles Quickly

Run a small tuning session against current data:

```bash
bijux vex nd tune --vector-store faiss --top-k 10 --samples 10
```

This reports per-profile latency and recommends a profile for your workload.

## Enable Witness Queries

Witness queries sample exact results for auditing.

```bash
--nd-witness-rate 0.1 \
--nd-witness-sample-k 3
```

Witness results are recorded in provenance.

## Read ND Stability Signals

ND results emit stability metrics:

- `rank_instability`
- `distance_margin`
- `similarity_entropy`
- `witness_report`

Use them to validate whether ND is appropriate for your workload.

## Calibrated Score Ranges

ND results include calibrated score ranges derived from the active metric.
Cross-backend score comparisons only make sense when metric + normalization are
identical.

## Replay Semantics

ND replay is only attempted when a seed is provided:

```bash
--randomness-seed 123
```

If you declare `--randomness-non-replayable`, replay is refused by design.

## Strict Replay Checks

ND replay refuses if the ANN index hash changes between runs. This prevents
false claims of replayability when the index has drifted.

## Build ANN Indexes Explicitly

Separate index building from query:

```bash
bijux vex materialize --execution-contract non_deterministic --index-mode ann
```

To rebuild:

```bash
bijux vex vdb rebuild --vector-store faiss --mode ann
```

If you need on-demand builds for development, opt in:

```bash
--nd-build-on-demand
```

## Warmup Queries

Use warmup queries to preheat caches and reduce first-query latency:

```bash
--nd-warmup-queries warmup_vectors.json
```

`warmup_vectors.json` should be a JSON array of vectors.

## Outlier Handling

ND can refuse low-signal queries:

```bash
--nd-outlier-threshold 0.2 --nd-adaptive-k
```

When the best neighbors are below the threshold, the run returns a
`nd_no_confident_neighbors` reason instead of low-quality results.

## SLO Reporting

ND runs report whether they met:

- `nd_latency_budget_ms`
- `nd_target_recall` (when witness is enabled)

This makes alerting and dashboards straightforward.

## Failure Guardrails

If the ND backend fails repeatedly, a circuit breaker refuses ND requests
for a short cooldown. Use `--trace` to view events.
