# Bijux Agent

Bijux Agent is a deterministic, auditable document-processing pipeline (CLI + optional HTTP API) designed to:

- process files or inline text,
- produce structured outputs,
- emit an audit trace suitable for replay validation and post-hoc inspection.

Published package name: `bijux-canon-agent`

## Quickstart (CLI)

```bash
make bootstrap
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export HUGGINGFACE_API_KEY=...
export DEEPSEEK_API_KEY=...

python -m bijux_canon_agent run path/to/file.txt --out artifacts/bijux-canon-agent/run1 --config examples/reference-config.yml
```

## Where to start

- **Using the tool**: `docs/user/usage.md`
- **Understanding the package layout**: `docs/project_overview.md`
- **Understanding the model**: `docs/overview/concepts.md`
- **Relying on guarantees**: `docs/spec/read_this_first.md`
- **Maintaining the repo**: `docs/maintainer/spec.md`
