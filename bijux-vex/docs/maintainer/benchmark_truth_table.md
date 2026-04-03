# Benchmark Truth Table

This document defines what Bijux Vex benchmarks measure, what they do not claim, and when results are comparable.

## Measurements

- `exact`:
Measures deterministic exact kNN latency and throughput on a fixed dataset.
Includes warmup time and steady-state timings.

- `ann`:
Measures ND latency and quality signals (`overlap@k`, instability estimates) under bounded ND settings.
Quality is estimated from sampled queries.

## Non-Claims

- Benchmarks do not certify production SLO compliance.
- ANN results do not imply full recall without witness verification.
- Results are not comparable across different datasets or dimensions.

## Comparability Rules

- Compare only within the same dataset size, dimension, and query count.
- Compare only within the same backend + mode pairing.
- Treat `status: todo` baselines as placeholders.

## Baseline Policy

- Baselines are committed as data.
- CI treats regressions as warnings until `status` is `measured`.
- Heavy benchmarks should be run on a dedicated host (not CI).
