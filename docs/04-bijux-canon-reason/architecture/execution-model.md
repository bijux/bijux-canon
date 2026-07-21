---
title: Execution Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-21
---

# Execution Model

`bijux-canon-reason` produces a claim only through an inspectable plan and an
event trace. Planning, tool execution, evidence registration, claim formation,
verification, and finalization are separate proof boundaries.

```mermaid
flowchart LR
    spec["ProblemSpec"]
    plan["content-addressed Plan"]
    execute["ordered plan execution"]
    evidence["evidence + support spans"]
    claims["typed claims"]
    trace["canonical trace"]
    verify["verification report"]
    artifacts["manifested run directory"]

    spec --> plan --> execute
    execute --> evidence --> claims --> trace --> verify --> artifacts
```

## Problem and Plan

`ProblemSpec` names the description, constraints, expected output type, and
optional expected result. Its ID is derived from content when the caller does
not supply one. The planner creates a directed plan whose nodes use five stable
kinds: `understand`, `gather`, `derive`, `verify`, and `finalize`.

Plan nodes name dependencies, tool requests, notes, and parameters. Node and
plan IDs are content-addressed, so a changed dependency, tool request, or
parameter produces different plan identity rather than silently reusing an old
one.

## Execution and Trace

The application validates the package system contract, resolves the spec ID,
plans the problem, and executes with fail-fast policy. A trace records the
ordered facts of execution:

- plan actions starting and finishing;
- tool calls and their results;
- evidence registrations; and
- claim emissions.

Finished actions use typed outputs. In addition to the five plan kinds, a run
can record `insufficient_evidence` explicitly. That result is a meaningful
reasoning outcome, not a transport failure.

The default runtime is seeded and local. A spec with `needs_retrieval` can use
the local BM25 runtime with a pinned corpus, chunk size, overlap, and BM25
parameters. Otherwise the package uses its deterministic fake runtime. A caller
may inject another `ExecutionRuntime`, but its kind, mode, tools, versions, and
configuration fingerprints become part of the retained runtime descriptor.

## Evidence and Claims

An evidence registration binds a URI, content hash, byte span, chunk ID, and
relative artifact path. A claim states whether it is derived, observed, or
assumed and whether it is proposed, validated, or rejected. Every support
reference names another claim, evidence item, or tool call and includes a byte
span and SHA-256 hash of the supported snippet.

This makes support inspectable at the byte level. A claim does not become
grounded merely because it cites a document ID; the verifier can check that the
referenced bytes exist, fit inside the evidence span, and hash to the recorded
snippet value.

## Verification

After execution, the verifier checks core invariants, tool linkage, claim
references, derived grounding, reasoning structure, insufficient-evidence
behavior, finalized-claim status, required plan actions, evidence hashes, and
support spans. The report retains every check, failure severity, invariant ID,
and summary count.

The run builder then adds the runtime fingerprint and invariant checksum to the
trace metadata, serializes the evidence set, fingerprints the trace file, and
builds a SHA-256 manifest for core and provenance files.

## Identity and Replay Boundary

The run ID is derived from spec identity, preset, seed, and runtime fingerprint.
Replay loads the original spec, plan, trace, runtime descriptor, and recorded
tool results. It validates the original invariant checksum before execution,
runs through a frozen runtime, checks the checksum again, and emits a separate
replay trace and structural diff.

The fingerprint comparison is therefore the end of a verification chain, not a
standalone equality test. A missing plan, changed pinned corpus, mismatched
retrieval provenance, or invalid checksum prevents replay from claiming
equivalence.

See [Artifact Contracts](../interfaces/artifact-contracts.md) for the on-disk
evidence set and [Failure Recovery](../operations/failure-recovery.md) for
triage.
