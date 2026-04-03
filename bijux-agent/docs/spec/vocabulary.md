# Vocabulary (spec)

This vocabulary defines terms as used in the spec.

## Core terms

- **Context**: the input mapping for a run (goal + input + identifiers).
- **Run**: one execution of the canonical pipeline over a context.
- **Phase**: a named lifecycle step in the canonical pipeline (e.g. `EXECUTE`).
- **Trace**: `run_trace.json`, the audit record of a run.
- **Trace entry**: one node in the trace with inputs, outputs, status, and metadata.
- **Verdict**: the final decision outcome recorded in `final_result.json`.
- **Epistemic status**: the system’s stated certainty level about the verdict.
- **Replayability**: a trace classification indicating whether deterministic replay validation is permitted.
- **Fingerprint**: a hash derived from pipeline definition + config snapshot used to identify a run.
- **Failure artifact**: an immutable structured description of a failure.

## Normative keywords

- **MUST**, **SHOULD**, **MAY**: used in the RFC sense (see `docs/spec/read_this_first.md`).
