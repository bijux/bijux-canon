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
| `research` | one `ResearchApplicationInput` JSON file | one immutable research record and manifest | research identity or JSON summary |
| `inspect` | a research identity | nothing | complete typed research record |
| `verify` | a research identity, or `trace.jsonl` and `plan.json` | `verify.verify.json` only in trace mode | exact restart verification or trace report |
| `replay` | a research identity, or a trace and sibling run artifacts | `replay/trace.jsonl` only in trace mode | replayed states or trace fingerprint data |
| `compare` | a research identity | nothing | attributed differences between adjacent attempts |
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

## Research records

`ResearchApplicationInput` is the installed handoff from admitted RAG evidence
and verified graph components into bounded RAR. Execute it and retain the
content-derived identity:

```bash
RESEARCH_ID=$(bijux-canon-reason research \
  --input research-input.json \
  --artifacts-dir artifacts/bijux-canon-reason)

bijux-canon-reason inspect --research-id "$RESEARCH_ID" \
  --artifacts-dir artifacts/bijux-canon-reason
bijux-canon-reason verify --research-id "$RESEARCH_ID" \
  --artifacts-dir artifacts/bijux-canon-reason
bijux-canon-reason replay --research-id "$RESEARCH_ID" \
  --artifacts-dir artifacts/bijux-canon-reason
bijux-canon-reason compare --research-id "$RESEARCH_ID" \
  --artifacts-dir artifacts/bijux-canon-reason
```

All five operations call `ResearchApplicationService`. The record retains the
input, graph synthesis, independently verified evidence paths, two immutable
attempts, replayed states, and an event-attributed comparison. Its manifest
binds the canonical record bytes. Inspection, verification, replay, and
comparison reject a changed record before returning results.

The `bijux-rar` compatibility command exposes these same operations by calling
the canonical application. It does not translate the input or maintain a
separate research store.

## `verify`

```bash
bijux-canon-reason verify \
  --trace "$RUN_DIR/trace.jsonl" \
  --plan "$RUN_DIR/plan.json" \
  --fail-on-verify \
  --json
```

In trace mode, both `--trace` and `--plan` are required existing files and
verification writes `verify.verify.json` beside the trace. This is deliberately
separate from the run-time `verify.json`. Research mode instead accepts
`--research-id` with `--artifacts-dir` and recomputes synthesis, provenance,
replay, and comparison from the manifested application input.

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

In trace mode, `--fail-on-diff` is enabled by default;
`--no-fail-on-diff` reports a mismatch without failing the command. Replay
always emits JSON, so `--json` is accepted but does not change its current
output format. The payload includes original and replayed fingerprints, a
structural diff summary, and the replay trace path. Research mode accepts
`--research-id`, replays the retained immutable attempt chain, and requires
exact parity with both persisted states.

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
and any case with verification failures makes the command exit `2`.
`exact_support_rate` and `support_links_per_supported_claim` recompute retained
evidence spans and digests as workflow diagnostics. They are not retrieval
relevance or semantic-faithfulness measurements.

## Scaffolding boundary

Create a minimal sample specification with:

```bash
bijux-canon-reason init init --target specs
```

The helper creates the target directory and writes `sample_spec.json`; if that
file already exists, it is preserved. The default target is `specs`.
