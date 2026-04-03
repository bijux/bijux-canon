# Why tracing exists

Tracing is not optional overhead; it is the point of the project.

## What tracing enables

- **Auditability**: decisions are accompanied by structured provenance.
- **Regression detection**: compare fingerprints and outcomes across versions.
- **Replay validation**: verify that a recorded run satisfies the trace contract.
- **Debugging**: correlate phases, agents, and failures without guessing.

## What tracing does not claim

- Tracing does not make a model “correct”.
- A REPLAYABLE trace does not guarantee the provider will return identical tokens in the future.
- A NON_REPLAYABLE trace can still be useful; it just must be labeled honestly.

## Practical implication

If you remove trace metadata, you remove the system’s ability to prove what happened.
The code is expected to fail fast rather than emit unverifiable artifacts.
