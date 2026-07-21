---
title: CLI Surface
audience: mixed
type: reference
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-21
---

# CLI Surface

The `bijux-canon-reason` command creates and inspects deterministic reasoning
run bundles. Use JSON output for automation and treat exit code `2` as a
governed verification, replay, or evaluation failure.

## Command map

| Command | Reads | Writes | Success output |
| --- | --- | --- | --- |
| `run` | one `ProblemSpec` JSON file | a complete run directory | run directory, or a JSON run summary |
| `verify` | `trace.jsonl` and `plan.json` | `verify.verify.json` beside the trace | `ok`, or a JSON verification report |
| `replay` | a trace and its sibling run artifacts | `replay/trace.jsonl` | JSON fingerprint and diff data |
| `eval` | `problems.jsonl` from a named suite | case runs, `cases.jsonl`, and `summary.json` | JSON containing the summary path, optionally with counts |

## `run`

```bash
bijux-canon-reason run \
  --spec problem.json \
  --preset default \
  --seed 0 \
  --artifacts-dir artifacts/bijux-canon-reason \
  --fail-on-verify \
  --json
```

Required and optional inputs:

| Option | Default | Meaning |
| --- | --- | --- |
| `--spec PATH` | required | Existing JSON file validated as a `ProblemSpec`. |
| `--preset NAME` | `default` | Planning/execution preset recorded with the run. |
| `--seed INTEGER` | `0` | Deterministic seed included in run identity. |
| `--artifacts-dir PATH` | `artifacts/bijux-canon-reason` | Root beneath which `runs/<run-id>/` is written. |
| `--fail-on-verify` | disabled | Exit `2` when the generated verification report contains failures. |
| `--json` | disabled | Emit `run_dir`, `verify_failures`, and summary metrics as one JSON object. |

Without `--fail-on-verify`, a run with verification findings is still written
and exits successfully. The caller must inspect `verify.json` or the
`verify_failures` JSON field before accepting it.

Every completed run directory contains:

| Path | Contract |
| --- | --- |
| `spec.json` | Content-addressed problem specification. |
| `plan.json` | Plan nodes, dependency edges, and identities. |
| `trace.jsonl` | Canonically serialized typed trace. |
| `verify.json` | Verification report produced during the run. |
| `fingerprint.txt` | Canonical trace-file fingerprint. |
| `run_meta.json` | Run, producer, runtime, schema, and invariant-checksum metadata. |
| `manifest.json` | Run-relative file digests for the initial bundle. |
| `evidence/` | Materialized evidence when the run registers evidence. |
| `provenance/` | Retrieval corpus, index, and provenance when retrieval is used. |

## `verify`

```bash
bijux-canon-reason verify \
  --trace "$RUN_DIR/trace.jsonl" \
  --plan "$RUN_DIR/plan.json" \
  --fail-on-verify \
  --json
```

Both `--trace` and `--plan` are required existing files. Verification writes
`verify.verify.json` beside the trace. This is deliberately separate from the
run-time `verify.json`.

Exit behavior deserves explicit handling:

| Mode | Findings present | Exit |
| --- | --- | --- |
| plain, default | yes or no | `0`, prints `ok` |
| plain, `--fail-on-verify` | yes | `2` |
| `--json` | no | `0` |
| `--json` | yes | `2`, even without `--fail-on-verify` |

For automation, use `--json` and inspect `status`, `failures`, and `checks`.

## `replay`

```bash
bijux-canon-reason replay \
  --trace "$RUN_DIR/trace.jsonl" \
  --fail-on-diff \
  --json
```

`--fail-on-diff` is enabled by default; `--no-fail-on-diff` reports a mismatch
without failing the command. Replay always emits JSON, so `--json` is accepted
but does not change its current output format. The payload includes original
and replayed fingerprints, a structural diff summary, and the replay trace
path.

Replay loads `spec.json`, `plan.json`, and `run_meta.json` from the trace's
directory, validates the recorded invariant checksum, and runs with recorded
tool returns. Retrieval runs additionally validate their recorded corpus,
index, and provenance digests. A fingerprint mismatch exits `2` unless
`--no-fail-on-diff` is selected.

## `eval`

```bash
bijux-canon-reason eval \
  --suite small \
  --preset default \
  --seed 0 \
  --artifacts-dir artifacts/bijux-canon-reason \
  --json
```

The suite loader resolves `<suite-root>/<suite>/problems.jsonl`. It first looks
for `tooling/evaluation_suites` and `benchmarks/suites` from the working tree,
then searches package ancestors. Each problem produces a governed run beneath
`eval/<suite>/case_<index>/`; aggregate case metrics go to `cases.jsonl` and
`summary.json`.

The default suite name is `small`. A missing suite fails before evaluation,
and any case with verification failures makes the command exit `2`. Metrics
such as the current retrieval recall and reciprocal-rank values are workflow
proxies based on whether evidence was registered; they are not benchmark-grade
relevance judgments.

## Scaffolding boundary

Create a minimal sample specification with:

```bash
bijux-canon-reason init init --target specs
```

The helper creates the target directory and writes `sample_spec.json`; if that
file already exists, it is preserved. The default target is `specs`.
