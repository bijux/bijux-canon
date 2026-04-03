STATUS: EXPLANATORY
# Usage

CLI commands are the primary entrypoints for deterministic runs.
Run the deterministic pipeline:

```bash
python -m bijux_rar run --spec path/to/spec.json --seed 42 --preset default
```

Verify a trace (optional plan tightens checks):

```bash
python -m bijux_rar verify --trace artifacts/runs/<run_id>/trace.jsonl --plan artifacts/runs/<run_id>/plan.json
```

Replay with drift detection:

```bash
python -m bijux_rar replay --trace artifacts/runs/<run_id>/trace.jsonl
```

Determinism gate:

```bash
make replay_gate
```
