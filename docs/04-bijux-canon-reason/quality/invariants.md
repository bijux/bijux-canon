---
title: Invariants
audience: mixed
type: reference
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-21
---

# Invariants

`bijux-canon-reason` makes the path from problem specification to claim
verification inspectable. A conclusion is represented as structured data tied
to a plan, trace events, evidence records, support spans, and content hashes.

## Structural invariants

| Surface | Invariant |
| --- | --- |
| plan | node identifiers are unique, every dependency exists, and the graph is acyclic |
| trace header | schema, runtime protocol, canonicalization version, and fingerprint algorithm are supported |
| trace order | event indices begin at zero and increase monotonically |
| tool linkage | every return references a known call and every call has a return |
| evidence linkage | evidence identifiers are unique and evidence events identify a plan step |
| lifecycle | started steps belong to the plan and reach a finished event |
| verification report | check names are unique |

These checks reject malformed reasoning history before its substantive claims
are considered.

## Evidence invariants

Evidence and support references use explicit spans and SHA-256 identities:

- evidence spans satisfy `0 <= start < end`;
- chunk and snippet hashes use 64 lowercase hexadecimal characters;
- evidence content paths are relative POSIX paths without drive prefixes,
  backslashes, empty segments, or `..` traversal;
- a support reference names its kind, target identifier, span, snippet hash,
  and hash algorithm;
- claim identifiers are derived from the statement, status, confidence,
  supports, claim type, and structured content.

Retrieval chunks record UTF-8 byte spans even though chunk boundaries are
selected over characters. Verification can therefore hash the exact persisted
bytes and detect a changed snippet, including text containing multibyte
characters.

## Verification sequence

```mermaid
flowchart LR
    core["core invariants"] --> tools["tool linkage"]
    tools --> supports["claim supports"]
    supports --> grounding["derived grounding"]
    grounding --> trace["reasoning trace"]
    trace --> insufficient["insufficiency handling"]
    insufficient --> finalize["validated finalization"]
    finalize --> steps["required steps"]
    steps --> hashes["evidence hashes"]
    hashes --> spans["support spans"]
```

The verifier runs this ordered registry and returns every check together with
structured failures. A finalized derived claim must not bypass its support
chain, and an insufficient-evidence outcome must be represented explicitly
rather than as a confident unsupported answer.

## Artifact invariants

A completed run persists the problem specification, content-addressed plan,
JSONL trace, verification report, trace fingerprint, run metadata, and manifest.
Retrieval-enabled runs also persist their corpus, index, and retrieval
provenance. The manifest hashes the evidence files it names.

The run identifier binds the specification, preset, seed, and runtime
fingerprint. Replay validates the original invariant checksum, retrieval
provenance, and frozen recorded tool results before producing a replay trace.
The replay checksum must still equal the recorded checksum; fingerprints and a
structured diff expose any remaining trace difference.

## Determinism boundary

Canonical JSON, stable identifiers, seeded local execution, frozen results,
and pinned retrieval artifacts make the reference workflow reproducible. A
caller-supplied runtime or tool is deterministic only to the extent described
by its recorded descriptor and outputs. The [test strategy](test-strategy.md)
separates this mechanical reproducibility from the semantic evaluation of
reasoning quality.
