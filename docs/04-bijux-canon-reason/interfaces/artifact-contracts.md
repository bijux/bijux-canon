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
invariant checksum. The invariant checksum covers the complete plan, the
ordered evidence IDs from the trace, and the runtime descriptor. It does not
cover every trace event or claim; `fingerprint.txt` and the manifest protect the
trace bytes.

The manifest covers all core files except itself, every file under
`provenance/`, and every evidence path registered by the trace. Verify the
manifest before exporting, comparing, or replaying a run.

## What Each Digest Proves

| Digest or identity | Inputs | Trust question answered |
| --- | --- | --- |
| run ID | spec ID, preset, seed, runtime fingerprint | which governed run configuration was selected |
| trace ID | typed events, metadata, linked IDs, protocol and canonicalization versions | whether the semantic trace content changed |
| trace fingerprint | exact `trace.jsonl` bytes | whether the serialized trace changed |
| invariant checksum | plan, evidence-ID order, runtime descriptor | whether execution structure and evidence ordering still agree |
| manifest entries | bytes of retained core, provenance, and evidence files | whether a retained file changed |

These values overlap by design but are not interchangeable. In particular, the
manifest does not include itself, and the invariant checksum is not a digest of
the entire trace.

## Acceptance Order

For an imported or retained run:

1. resolve the run below the configured artifact root without following an
   untrusted path;
2. parse `manifest.json` as a relative-path-to-SHA-256 mapping;
3. hash every listed file, reject missing or extra required core files, and do
   not treat the manifest as self-authenticating;
4. compare `fingerprint.txt` with the exact bytes of `trace.jsonl`;
5. load the spec, plan, trace, report, and runtime descriptor through their typed
   readers;
6. recompute the invariant checksum and semantic trace identity; and
7. inspect verification failures before accepting any final claim.

When the run crosses a trust boundary, authenticate the manifest with an
external signature or trusted digest. Internal consistency can reveal changed
files, but it cannot prove who produced the directory.

## Resource Enforcement

Optional environment limits can cap aggregate run-disk use, wall-clock time,
CPU time, and retrieval corpus bytes. A limit failure means the run did not
complete its artifact contract. Do not publish its directory as verified
evidence merely because some core files were already written.

See [Execution Model](../architecture/execution-model.md) for how the files are
produced.
