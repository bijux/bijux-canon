---
title: CLI Surface
audience: mixed
type: reference
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-07-21
---

# CLI Surface

The `bijux-canon-agent` command processes one file or the immediate files in a
directory, then writes a compact result and trace. Its public command surface
contains `run`; a hidden `replay` command remains callable for stored-outcome
comparison.

## Credential precondition

Before parsing any command, the entrypoint loads `.env` when
`python-dotenv` is available and requires all of these variables:

- `OPENAI_API_KEY`;
- `ANTHROPIC_API_KEY`;
- `HUGGINGFACE_API_KEY`;
- `DEEPSEEK_API_KEY`.

This check currently applies to `--help`, `--version`, `--dry-run`, and
`replay` as well as provider-backed execution. A missing key exits `1` before
argument validation. Keep credentials in the process environment or a secret
manager, never in the YAML configuration.

## `run`

```bash
bijux-canon-agent run INPUT \
  --out OUTPUT_DIRECTORY \
  --config AGENT_CONFIG
```

| Argument or option | Required | Meaning |
| --- | --- | --- |
| `INPUT` | yes | Existing file or directory. A directory contributes only immediate regular files; traversal is not recursive. |
| `--out PATH` | yes | Directory for `result/` and `trace/` artifacts. |
| `--config PATH` | no | YAML configuration. The parser default is `examples/reference-config.yml`, resolved from the current working directory. |
| `--dry-run` | no | Resolve inputs and report simulated successes without invoking the pipeline. |
| `--replay TRACE` | no | Require the named trace to exist and record its path in logs. It does not currently alter or validate the new run. |

Use an explicit configuration path. A missing configuration only produces a
warning and an empty configuration, but a non-dry run later requires a
`model_metadata` object to write its trace. In a repository checkout, the
maintained example is
`packages/bijux-canon-agent/examples/reference-config.yml`.

At minimum, replayable trace production requires:

```yaml
task_goal: summarize the retention obligations without unsupported claims
model_metadata:
  provider: local
  model_name: auditable-doc-pipeline
  temperature: 0.0
  max_tokens: 512
logging:
  log_dir: artifacts/bijux-canon-agent/logs
  structured_logging: true
```

### Inputs and batch behavior

For a file, the pipeline processes that one path. For a directory, every
immediate regular file is attempted; unsupported content can fail during file
reading. Files are accumulated as `successful` or `failed` records.

Individual file failures do not make the command exit nonzero. If at least one
file succeeds, the first success becomes the primary artifact. If none
succeeds, the command writes a fallback veto result without a trace and still
returns normally unless a command-level exception occurs. Automation must
inspect the logs and artifacts rather than relying on exit status alone.

For exactly one successful input, stdout includes the full structured pipeline
result. Batch runs do not print each result to stdout.

### Output layout

```text
OUTPUT_DIRECTORY/
├── result/
│   └── final_result.json
└── trace/
    └── run_trace.json
```

`run_trace.json` exists only when a primary non-dry success is available.
`final_result.json` contains verdict, confidence, epistemic status, stop and
termination data, convergence data, runtime/model metadata, and the relative
trace path.

Both files use fixed names and are written directly. Reusing an output
directory can overwrite earlier evidence, and no manifest binds the pair.

### Dry run

```bash
bijux-canon-agent run document.md \
  --out artifacts/bijux-canon-agent/dry-run \
  --config packages/bijux-canon-agent/examples/reference-config.yml \
  --dry-run
```

Dry run resolves the input paths but does not read them through the pipeline.
It writes `final_result.json` with a fallback `veto`, confidence `0.0`, and a
null trace path. Those values are simulation markers, not a judgment about the
document.

## `replay`

```bash
bijux-canon-agent replay OUTPUT_DIRECTORY/trace/run_trace.json
```

The command:

1. upgrades an unversioned v1 payload to trace schema v2 when supported;
2. checks the supported schema version, runtime compatibility, run ID, and a
   non-empty entry list;
3. deserializes the trace and reconstructs its terminal pipeline result;
4. prints decision, confidence, and stop reason;
5. compares decision, confidence, epistemic verdict, and stop reason with
   `OUTPUT_DIRECTORY/result/final_result.json` when present.

A missing trace exits `2`; a load or validation error exits `1`. A reported
`MISMATCH` does not currently change the exit status, and the comparison does
not cover termination reason, convergence fields, runtime version, model
metadata, run fingerprint, input bytes, or the full role output. Treat the
printed `MATCH` as four-field summary parity only.
