# Example: minimal CLI run

This is the fastest way to confirm the CLI, config parsing, and artifact writing are wired correctly.

## 1) Create an input file

```bash
mkdir -p examples/tmp
cat > examples/tmp/input.txt << 'EOF'
This is a small input document.
EOF
```

## 2) Run the pipeline

```bash
python -m bijux_agent.main run examples/tmp/input.txt --out artifacts/minimal --config config/config.yml
```

If processing exactly one file and the run succeeds, the CLI prints the computed JSON result to stdout.

## 3) Inspect artifacts

```bash
ls -R artifacts/minimal
```

You should see (paths relative to the run directory):

- `result/final_result.json`
- `trace/run_trace.json`

For the meaning of these files, see `docs/spec/execution_artifacts.md`.
