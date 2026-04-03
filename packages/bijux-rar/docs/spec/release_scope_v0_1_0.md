
## Release Scope — v0.1.0
STATUS: AUTHORITATIVE

This document freezes the scope for v0.1.0. No new features are accepted after this point—only bug fixes and documentation clarifications.

## Guaranteed (stable in v0.x)
- Deterministic trace, replay, and verification invariants (see [system_contract.md](system_contract.md) and [core_contracts.md](core_contracts.md)).
- CLI surface: `init`, `run`, `verify`, `replay`, `eval` commands and their documented flags.
- Trace schema version and fingerprinting rules.
- Public Python imports under `bijux_rar.*` already documented in [doc_to_code_map.md](doc_to_code_map.md).

## Experimental (may change within v0.x)
- Evaluation metrics taxonomy (metrics names may expand).
- Benchmark harness outputs and thresholds.
- Optional extras in `pyproject.toml` (extras API surface may evolve).

## Explicitly Excluded (not supported in v0.1.0)
- Non-deterministic reasoning backends enabled by default (LLM is opt-in and frozen).
- Hybrid retrieval backends (only the shipped deterministic chunked BM25 is supported).
- Breaking changes to verification leniency modes (only documented policies apply).

## May Break Before v1.0 (with notice)
- Internal file layout inside `artifacts/` but not the mandatory contract files (`spec.json`, `plan.json`, `trace.jsonl`, `verify.json`, `manifest.json`, provenance snapshots).
- Additional CLI flags marked experimental in help text.
- Optional dependency versions and extras composition.
