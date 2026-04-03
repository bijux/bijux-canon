# Start Here in 10 Minutes

1) Install

```bash
pip install bijux-vex
```

2) Deterministic example

```bash
bijux vex ingest --doc "hello" --vector "[0.0, 1.0, 0.0]" --vector-store memory
bijux vex materialize --execution-contract deterministic --vector-store memory
bijux vex execute --artifact-id art-1 --execution-contract deterministic \
  --execution-intent exact_validation --execution-mode strict --vector "[0.0, 1.0, 0.0]"
```

3) ND example

```bash
bijux vex materialize --execution-contract non_deterministic --index-mode ann \
  --vector-store faiss --vector-store-uri ./index.faiss
bijux vex execute --artifact-id art-1 --execution-contract non_deterministic \
  --execution-intent exploratory_search --execution-mode bounded \
  --randomness-seed 42 --randomness-sources ann_probe --nd-witness sample \
  --vector "[0.0, 1.0, 0.0]"
```

4) Inspect provenance

```bash
bijux vex explain --result-id <result_id> --artifact-id art-1
```
