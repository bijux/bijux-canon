# minimal-run  

**Scope:** Smallest end-to-end walkthrough.  
**Audience:** Users validating behavior.  
**Guarantees:** One traceable run with replay and diff.  
**Non-Goals:** Full feature coverage.  
Why: This doc exists to record its single responsibility for review.  

## Overview  
This walkthrough uses one flow, one agent, one retrieval, and one verification failure to show the full lifecycle: run → persist → replay → diff.  

## Flow  
The flow has a single step that calls one agent, performs one retrieval, and emits reasoning that fails a verification gate.  

## Run  
```bash
agentic-flows run examples/minimal/flow.json --db-path /tmp/flows.duckdb
```

## Persist  
The run persists automatically to DuckDB at the provided path.  

## Replay  
```bash
agentic-flows inspect run <run_id> --tenant-id <tenant> --db-path /tmp/flows.duckdb
```

## Diff  
```bash
agentic-flows diff run <run_a> <run_b> --tenant-id <tenant> --db-path /tmp/flows.duckdb
```

## Verification Failure  
This flow triggers a verification failure because the retrieved evidence contradicts the reasoning claim. The diff surfaces the verification conflict instead of accepting the run.  
