# Usage

Bijux Agent is a deterministic, auditable document-processing pipeline with a CLI and an optional HTTP API.

## Install

Development (recommended):

```bash
make bootstrap
```

Minimal (no dev tooling):

```bash
python -m pip install -e .
```

## Configure API keys

The CLI currently validates that *all* providers below are configured before it will run:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `HUGGINGFACE_API_KEY`
- `DEEPSEEK_API_KEY`

Put them in a `.env` file at the repository root, or export them in your shell.

## Run

Process a single file:

```bash
python -m bijux_agent.main run path/to/file.txt --out artifacts/run1 --config config/config.yml
```

Process a directory (non-recursive; files directly under the directory):

```bash
python -m bijux_agent.main run path/to/dir --out artifacts/run1 --config config/config.yml
```

Dry-run (no model calls; validates discovery + wiring only):

```bash
python -m bijux_agent.main run path/to/file.txt --out artifacts/run1 --config config/config.yml --dry-run
```

## Outputs

`--out <DIR>` is treated as a single *run directory*. The CLI writes:

- `<DIR>/result/final_result.json` — compact, human-friendly verdict summary
- `<DIR>/trace/run_trace.json` — machine-checkable run trace (for auditing/replay tooling)
- logs under the configured `logging.log_dir` (from your YAML config)

If exactly one file is processed and succeeds, the CLI also prints the computed `result` JSON to stdout.

## Replay

Replay is a *verification* tool: it reads a trace and reports whether the recorded run is internally consistent.

```bash
python -m bijux_agent.main replay artifacts/run1/trace/run_trace.json
```

Replay does not re-run models.

## Configuration quick reference

The CLI reads the YAML config passed via `--config`.

Minimum required keys for trace construction:

```yaml
task_goal: "summarize this document"
model_metadata:
  provider: "local"
  model_name: "auditable-doc-pipeline"
  temperature: 0.0
  max_tokens: 512
```

For the normative contract (what is guaranteed vs best-effort), see `docs/spec/read_this_first.md`.

## Troubleshooting

- **“Missing API keys …”**: the current CLI is intentionally strict. Configure all keys or change `bijux_agent.config.env.validate_keys()` to validate only the selected backend.
- **Empty input directory**: the CLI only processes files directly under the directory; it does not recurse.
- **Where are the logs?**: check `logging.log_dir` in the YAML config (default in `config/config.yml`).
