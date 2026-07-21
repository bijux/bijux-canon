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

## Compatibility Boundary

Changing schema version, fingerprint inputs, metric meaning, scoring version,
run-file semantics, or replay equivalence is a contract change. Adding optional
diagnostic fields is safe only when existing readers ignore unknown metadata;
strict API payloads require their schema to evolve explicitly.

See [Execution Model](../architecture/execution-model.md) for the lifecycle that
produces these artifacts.
