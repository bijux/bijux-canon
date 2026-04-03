
STATUS: AUTHORITATIVE
## Glossary (Hostile Precision)

- Terms are locked; adding or changing definitions requires a formal version bump.
- Vocabulary is fixed; new words must be added here before appearing in specs.
- **Verification**: Checking structural/provenance invariants. Does not mean factual correctness. Does not mean semantic truth.
- **Evidence**: Chunked, hashed byte spans stored under artifacts. Does not include model output or summaries.
- **Citation**: `[evidence:<id>:<b0>-<b1>:<sha256>]` marker plus SupportRef. Anything else is rejected.
- **Replay**: Re-execution using pinned artifacts/config. Not log playback, not stochastic simulation.
- **Insufficient Evidence**: Explicit signal that required supports are absent. Not an error mask; verifier treats it as a distinct outcome.
- **Undefined Behavior**: Any state not covered by schemas/invariants; no guarantees are made and behavior may change without notice.

Terminology Lock:
- Definitions above are locked. Changing a definition is a breaking change and requires a major version bump with migration guidance.***
