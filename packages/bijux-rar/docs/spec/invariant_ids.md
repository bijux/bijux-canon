STATUS: AUTHORITATIVE

## Invariant IDs

- INV-DET-001: Trace replay MUST reproduce fingerprints when corpus/index/provenance match.
- INV-GRD-001: Derived claims MUST cite evidence via `[evidence:<id>:<b0>-<b1>:<sha256>]`; hashes over evidence bytes.
- INV-ART-001: All artifacts MUST reside under `artifacts/runs/<run_id>/`; root writes are forbidden.
- INV-SCH-001: Only supported schema versions MAY be consumed; unknown versions are rejected.
- INV-ORD-001: Trace events MUST be strictly ordered by `idx` and plan dependencies.
- INV-LNK-001: Every `tool_returned` MUST have a matching `tool_called`; linkage failures invalidate the run.***
