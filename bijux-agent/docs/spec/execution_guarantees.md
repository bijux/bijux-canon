# Execution guarantees (spec)

This document describes what a caller can rely on after invoking a run.

## CLI guarantees (normal run)

For `python -m bijux_agent.main run …` without `--dry-run`:

- The CLI MUST create a run directory at `--out`.
- The CLI MUST write `result/final_result.json`.
- The CLI MUST write `trace/run_trace.json`.
- The trace MUST validate (or be upgradeable) under the local trace schema.

## CLI guarantees (dry-run)

For `run --dry-run`:

- The CLI MUST validate input discovery and configuration loading.
- The CLI MUST write `result/final_result.json`.
- The CLI MUST NOT claim model-computed content.
- The CLI MAY skip producing a trace.

## API guarantees (v1)

For `POST /v1/run`:

- The handler MUST validate the request payload with the v1 schema.
- The handler MUST return a structured response with `success` and `context_id`.
- On failure, the handler MUST return a structured `error` object.

## Non-guarantees

- No guarantee that outputs are “correct” or “complete”.
- No guarantee of identical outputs across time, even under temperature 0 (providers can change).
- No guarantee of stable performance, throughput, or token usage.
