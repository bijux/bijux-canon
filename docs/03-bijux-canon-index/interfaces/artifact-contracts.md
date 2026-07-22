---
title: Artifact Contracts
audience: mixed
type: reference
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-07-21
---

# Artifact Contracts

Index evidence is split between the execution artifact, the run directory, and
the result payload. Keeping those layers separate prevents a result list from
being mistaken for a reproducible execution record.

## Execution Artifact

`ExecutionArtifact` binds a vector corpus to an execution contract:

| Field group | Contract |
| --- | --- |
| identity | `artifact_id`, schema `v1`, artifact version `1.0` |
| content | corpus and ordered-vector fingerprints |
| scoring | metric and scoring version |
| governance | deterministic or non-deterministic execution contract |
| construction | build parameters and index configuration fingerprint |
| lifecycle | index state, cold-start readiness, warm-cache hint |
| execution | execution ID, plan, and signature |
| evidence | approximation and determinism reports |

Only the supported schema and artifact versions are accepted. Materialization
requires an active transaction, and an existing artifact ID cannot be rebound
to a different execution contract.

The vector fingerprint covers ordered vector values. The configuration
fingerprint covers index construction policy. The backend and determinism
fingerprints are recorded separately at run time. Together they identify the
conditions that produced retrieval behavior.

## Run Directory

The default run root is `artifacts/bijux-canon-index/runs`; set
`BIJUX_CANON_INDEX_RUN_DIR` to relocate it. Each run has a dedicated directory:

```text
<run-id>/
├── metadata.json
├── result.json
└── status.json
```

Writes are atomic at the individual file boundary. `status.json` is written as
`incomplete` first. `result.json` is persisted before the status changes to
`complete`. A governed failure records `failed`, a reason, and optional details.

`metadata.json` captures:

- execution, artifact, and correlation identity;
- normalized request policy and ANN parameters;
- selected backend and redacted vector-store URI;
- backend exact/ANN capabilities and consistency description;
- ANN index information when applicable; and
- vector, configuration, backend, and determinism fingerprints.

`result.json` captures the primitive execution result, ordered vector IDs, and
the non-deterministic decision trace when present.

The run directory is a lifecycle record, not an append-only evidence bundle.
`RunStore.load()` accepts only `complete`; it refuses `incomplete` and `failed`
runs even when `metadata.json` or `result.json` exists. Preserve `status.json`
with the other files because it is the commit marker for this three-file
protocol.

## Result and Explanation Payloads

An execution response contains ordered vector IDs plus the correlation,
contract, replayability, and execution identity required to find its evidence.
An explanation resolves one result to its document, chunk, vector, artifact,
metric, score, rank-producing execution, and contract.

Replay returns both fingerprints, a Boolean match result, structured mismatch
details, non-deterministic sources, the enforced contract, replayability, and
the related execution ID. A non-deterministic replay may be acceptable without
being byte-identical; the details field states the applied equivalence rule.

## Safe Retention and Comparison

For an auditable retrieval decision, retain the artifact definition and the
complete run directory together. Copying only `result.json` loses the backend,
configuration, and determinism context required for interpretation.

Compare artifacts by content and configuration fingerprints before comparing
result order. Compare runs through their recorded metadata and execution
results. A result mismatch is evidence to investigate, while a missing or
changed contract is grounds to refuse equivalence.

## Evidence Join Procedure

To audit one returned vector:

1. use the response `execution_id` to locate the execution ledger record;
2. list runs, select the correlation-prefixed directory whose metadata matches
   the response correlation ID, and require its status to be `complete`;
3. confirm that `metadata.json` names the expected artifact and fingerprints;
4. find the vector in the ordered IDs and primitive result rows;
5. resolve vector, chunk, and document through the ledger; and
6. compare the artifact contract and fingerprints before replaying or comparing
   scores.

The run files are not self-authenticating. Atomic replacement protects each
JSON file from a partial write, but there is no run manifest or signature that
binds the three files together. If a run crosses a trust boundary, package it
with an external digest or signature and verify that envelope before loading.

## Run-Store Trust Assumptions

`RunStore` is a compact local lifecycle store, not a hostile-input or
multi-writer repository boundary.

| Assumption or limit | Current behavior | Operational consequence |
| --- | --- | --- |
| run identifiers are trusted | `run_id` becomes a directory component without a package-level identifier policy | validate identifiers before accepting them from an external caller |
| one writer owns a run | file replacement is atomic, but there is no run lock or compare-and-swap protocol | concurrent writers using one run ID can overwrite one another's metadata, result, or status |
| files share a trusted directory | no manifest binds the three JSON files | verify an external envelope before moving or loading a run directory |
| metadata and result fit local resources | JSON reads have no package-level byte, nesting, or record limit | enforce filesystem and payload limits at the deployment boundary |
| completion is the commit marker | `load()` accepts only `status == "complete"` | never infer completion from the presence of `result.json` |
| one file replacement is durable enough | the store does not issue an explicit filesystem sync | process-crash atomicity does not establish storage-device durability |

These limits do not invalidate the local protocol; they define where a higher
assurance deployment must add identifier validation, locking, authenticated
manifests, resource controls, and durability policy.

## Compatibility Boundary

Changing schema version, fingerprint inputs, metric meaning, scoring version,
run-file semantics, or replay equivalence is a contract change. Adding optional
diagnostic fields is safe only when existing readers ignore unknown metadata;
strict API payloads require their schema to evolve explicitly.

See [Execution Model](../architecture/execution-model.md) for the lifecycle that
produces these artifacts.
