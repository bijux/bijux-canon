---
title: Artifact Contracts
audience: mixed
type: reference
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-21
---

# Artifact Contracts

A reason run is a directory of mutually constraining evidence. No single file
is authoritative by itself: the manifest, trace fingerprint, invariant
checksum, and typed models protect different parts of the record.

## Run Layout

Under the selected artifact root, each content-addressed run uses this shape:

```text
runs/<run-id>/
├── spec.json
├── plan.json
├── trace.jsonl
├── verify.json
├── fingerprint.txt
├── run_meta.json
├── manifest.json
├── provenance/                 # present when retrieval produces evidence
│   ├── corpus.jsonl
│   ├── chunks.jsonl
│   ├── retrieval_provenance.json
│   └── index/bm25_index.json
└── replay/                     # created by replay
    └── trace.jsonl
```

The CLI defaults the artifact root to `artifacts/bijux-canon-reason`.

## Core Files

| File | Authority |
| --- | --- |
| `spec.json` | normalized problem, constraints, expected output, content ID |
| `plan.json` | nodes, dependencies, tool requests, edges, plan ID |
| `trace.jsonl` | canonical header followed by ordered typed events |
| `verify.json` | checks, failures, severities, invariant IDs, summary metrics |
| `fingerprint.txt` | SHA-256 fingerprint of the exact trace bytes |
| `run_meta.json` | IDs, preset, seed, runtime descriptor, checksums, producer version |
| `manifest.json` | sorted mapping from retained relative path to SHA-256 |

The JSON writer uses canonical serialization. Trace JSONL forces newline
stability across platforms because line-ending drift would change the recorded
fingerprint.

## Trace Contract

The first JSONL record is `trace_header`. It names trace, spec, and plan IDs;
runtime protocol and schema versions; fingerprint algorithm; canonicalization
version; and trace metadata. Every following record is a typed trace event.

The event order is evidence. Tool results link back to call IDs, evidence and
claims link to the action that produced them, and finished actions expose a
typed output. Reordering equivalent-looking events is still a trace change.

## Evidence Contract

Evidence paths are relative POSIX paths. Absolute paths, drive prefixes,
backslashes, parent traversal, and empty path segments are rejected. Before the
manifest is written, every registered evidence file must exist under the run
directory and match its declared SHA-256.

`SupportRef` narrows a claim to an exact byte interval and snippet hash. Valid
spans satisfy `0 <= start < end`; hashes use 64 lowercase hexadecimal
characters. Verification also checks the span against the registered evidence
and, when retrieval artifacts exist, against the chunk manifest.

## Runtime and Invariant Identity

`run_meta.json` retains the runtime kind and mode, tool names and versions,
configuration fingerprints, producer version, runtime fingerprint, and
invariant checksum. The checksum covers the plan, trace, and runtime descriptor.
It detects a cross-file change that could remain invisible when inspecting one
file in isolation.

The manifest covers all core files except itself, every file under
`provenance/`, and every evidence path registered by the trace. Verify the
manifest before exporting, comparing, or replaying a run.

## Resource Enforcement

Optional environment limits can cap aggregate run-disk use, wall-clock time,
CPU time, and retrieval corpus bytes. A limit failure means the run did not
complete its artifact contract. Do not publish its directory as verified
evidence merely because some core files were already written.

See [Execution Model](../architecture/execution-model.md) for how the files are
produced.
