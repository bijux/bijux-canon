
## Determinism Guarantees
STATUS: AUTHORITATIVE

Guaranteed deterministic:
- Fingerprints (sha256 over canonical bytes).
- Trace event ordering and IDs (stable_id).
- Chunking (UTF-8 byte spans, fixed params).
- BM25 ranking (rounded scores, doc-id tiebreak).

Conditionally deterministic:
- Execution with identical corpus/index/provenance and runtime config.
- Reasoner when backend is deterministic; LLM backends are opt-in and non-deterministic.

Not deterministic:
- Any external network/LLM call unless frozen and replayed.
- Host-level nondeterminism outside artifacts (e.g., filesystem reordering).

Environment assumptions:
- POSIX-style paths recorded; symlinks resolved strictly.
- Locale-independent tokenization; stable float rounding.
- Hashing algorithm fixed to sha256.

Undefined behavior:
- Running with missing provenance or altered artifacts.

### Determinism Matrix

| Component              | Deterministic | Conditions                                       | Notes                                      |
| ---------------------- | ------------- | ------------------------------------------------ | ------------------------------------------ |
| Fingerprints           | Yes           | Canonical bytes + sha256                         | Changes in canonicalization_version break  |
| Trace event order/IDs  | Yes           | Stable plan + execution path                     | Reordering or mutation invalidates run     |
| Chunking               | Yes           | UTF-8 spans, fixed chunk/overlap params          | Locale/time do not affect chunking         |
| BM25 ranking           | Yes           | Same corpus/index, score rounding, doc-id tiebreak| Float drift mitigated via rounding         |
| Replay                 | Yes           | Provenance hashes match; artifacts intact        | Drift → failure                            |
| Reasoner (deterministic)| Yes          | Deterministic backend only                       | LLM/non-deterministic backends are opt-in  |
| External tools         | No            | Unless frozen outputs recorded                   | Live calls break determinism               |

Scope Closure:
- Does NOT restate trace schema; see [trace_format.md](trace_format.md).
- Does NOT define verifier policies; see [verification_model.md](verification_model.md).
- Does NOT define lifecycle states; see [trace_lifecycle.md](trace_lifecycle.md).

BREAKING_IF_CHANGED: true

You understand this document if and only if you can answer:
- Which components are deterministic vs conditional vs non-deterministic.
- What conditions are required for replay to be deterministic.
- How environment assumptions (locale, hashing, paths) affect determinism.***
