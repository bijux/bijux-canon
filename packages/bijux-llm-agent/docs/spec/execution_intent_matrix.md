# Execution intent matrix (spec)

This matrix clarifies which artifacts are expected for each execution intent.

| Intent | Surface | Pipeline executed | `final_result.json` | `run_trace.json` |
| --- | --- | --- | --- | --- |
| Normal run | `main run` | Yes | Yes | Yes |
| Dry-run | `main run --dry-run` | No (simulated) | Yes | Optional |
| Replay | `main replay` | No | No | Input only |

Notes:

- Dry-run exists for wiring checks and file discovery validation.
- Replay validates recorded outcomes; it is not a model re-execution mechanism.
