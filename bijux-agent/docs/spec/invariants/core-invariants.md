# Core invariants (spec)

These invariants must hold across refactors. If an invariant must change, treat it as a breaking change and bump the relevant schema/version.

## Documentation invariant

- Every `docs/**/*.md` file MUST be tracked in `docs/doc_checksums.json`.
- `docs/index.md` MUST list every tracked documentation file.

(This is enforced by tests.)

## Canonical pipeline invariant

- The canonical phase order and allowed transitions MUST remain stable at runtime.
- Any intentional change MUST be accompanied by a clear versioning decision and updated spec text.

## Failure taxonomy invariant

- Every `FailureClass` MUST have a profile.
- Failure artifacts MUST validate against taxonomy profiles.

## Trace identity invariant

- Traces MUST record schema version, runtime version, and model metadata.
- Replayability MUST be classified in the trace header.

See also:

- `docs/spec/invariants/determinism.md`
- `docs/spec/failure_model.md`
