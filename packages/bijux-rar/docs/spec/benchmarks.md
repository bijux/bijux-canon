STATUS: EXPLANATORY
# Benchmark reproducibility

- Benchmarks run via `pytest-benchmark`; results stored under `artifacts/test/benchmarks`.
- Use the same Python version and dependencies (see `pyproject.toml`) to compare runs.
- Do not compare benchmarks across machines unless normalized by CPU; instead, use the regression thresholds enforced in `tests/perf/test_retrieval_benchmark.py`.
- Always run with `PYTHONDONTWRITEBYTECODE=1` to avoid filesystem noise.
