# boring-path  

**Scope:** Single end-to-end example.  
**Audience:** Users validating the simplest workflow.  
**Guarantees:** One deterministic run and replay.  
**Non-Goals:** Advanced features or optimizations.  
Why: This doc exists to record its single responsibility for review.  

## Overview  
This is the boring path: one flow, one agent, deterministic replay, DuckDB-backed, using both CLI and API.  

## Files  
- `examples/boring/flow.json`  
- `examples/boring/policy.json`  

## CLI  
```bash
agentic-flows run examples/boring/flow.json --policy examples/boring/policy.json --db-path /tmp/flows.duckdb
agentic-flows replay examples/boring/flow.json --policy examples/boring/policy.json --run-id <run_id> --tenant-id tenant-a --db-path /tmp/flows.duckdb
agentic-flows inspect run <run_id> --tenant-id tenant-a --db-path /tmp/flows.duckdb
```

## API  
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Agentic-Gate: gate-boring" \
  -H "X-Determinism-Level: strict" \
  -H "X-Policy-Fingerprint: <policy_fingerprint>" \
  -d '{"flow_manifest":"file://examples/boring/flow.json","inputs_fingerprint":"<inputs_fingerprint>","run_mode":"live","dataset_id":"retrieval_corpus","policy_fingerprint":"<policy_fingerprint>"}' \
  http://127.0.0.1:8000/api/v1/flows/run

curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Agentic-Gate: gate-boring" \
  -H "X-Determinism-Level: strict" \
  -H "X-Policy-Fingerprint: <policy_fingerprint>" \
  -d '{"run_id":"<run_id>","expected_plan_hash":"<plan_hash>","acceptability_threshold":"exact_match","observer_mode":false}' \
  http://127.0.0.1:8000/api/v1/flows/replay
```
