# Exact execution example

```bash
bijux vex ingest --doc "hello" --vector "[0.1,0.2]"
bijux vex materialize --execution-contract deterministic
bijux vex execute --artifact-id art-1 --vector "[0.1,0.2]" --top-k 1 \
  --execution-contract deterministic --execution-intent exact_validation --execution-mode strict
```

Expected:

- deterministic plan, no randomness sources
- execution artifact with no approximation report
- replay returns identical results

Failure example:

- If backend lacks deterministic support, command fails with InvariantError.
