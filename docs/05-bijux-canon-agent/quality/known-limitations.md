---
title: Known Limitations
audience: mixed
type: reference
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-07-21
---

# Known Limitations

The package governs orchestration state and evidence. It does not make a model
deterministic, turn confidence into calibrated truth, or provide deployment
isolation for tools and credentials.

## Model limits

- A model can produce an incorrect result that satisfies the output schema.
- Agent confidence is bounded structurally but is not automatically calibrated
  against real-world correctness.
- Temperature zero is required for the package's replayable designation, but a
  provider may still change model weights, serving infrastructure, or hidden
  behavior. Record provider, model name, token bound, runtime version, and
  prompt/model hashes.
- Live-provider tests require external credentials and service availability;
  they are separate from deterministic default evidence.

## Convergence limits

Convergence means a configured strategy observed stability or another declared
condition. Stable agents can agree on a wrong result, oscillation detection can
stop before discovering a better result, and a maximum-iteration stop is not
success. Consumers must inspect the convergence type, reason, decision
artifact, epistemic verdict, and termination reason together.

The canonical workflow is intentionally opinionated. Custom graphs can use the
workflow primitives, but they do not inherit the standard lifecycle's evidence
unless they declare and validate equivalent transitions and trace fields.

## Replay limits

Trace reconstruction proves that deterministic fields and recorded metadata
are coherent. It does not re-create an external provider's historical serving
environment. Timestamps are observational and excluded from deterministic
snapshots. A trace with incomplete replay fields or non-zero temperature is
non-replayable by contract.

Replay evidence also depends on retained inputs and artifacts. A hash can show
that content changed; it cannot recover content that was never stored.

## CLI and credential limits

The current CLI validates all four registered provider keys before parsing the
selected command. Consequently, help, dry-run, and replay invocation through
that entry point require `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`HUGGINGFACE_API_KEY`, and `DEEPSEEK_API_KEY`, even when the chosen operation
does not contact every provider. Library APIs and focused trace utilities do
not inherently require all four keys.

This behavior is stricter than least-privilege command-specific validation and
should be accounted for in local automation. Never place keys in trace
metadata, configuration snapshots, logs, or committed fixtures.

## Operational boundary

The package writes trace and result artifacts and provides structured failure
handling. It is not a process sandbox, distributed scheduler, secrets manager,
or durable multi-host event store. File access, provider rate limits, network
policy, cancellation, tenant isolation, artifact retention, and recovery
remain responsibilities of the host and `bijux-canon-runtime` where applicable.
