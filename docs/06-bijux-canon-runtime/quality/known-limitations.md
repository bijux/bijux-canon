---
title: Known Limitations
audience: mixed
type: reference
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-07-21
---

# Known Limitations

Runtime governance makes authority and divergence visible. It does not make an
external tool trustworthy, convert structural verification into factual truth,
or provide distributed infrastructure by itself.

## Execution limits

- The default library call selects live, strict execution, but a non-plan run
  still requires an explicit execution store and, for live/observe/unsafe,
  verification policy. Defaults do not create hidden production resources.
- `unsafe` is an explicit escape surface. It records relaxed configuration and
  requires a finalized trace, but it does not enforce live mode's full
  verification-coverage rule. Its results must not be labeled equivalent to a
  governed live run.
- `dry-run` exercises resolution, event, artifact, and persistence contracts
  through a simulated executor. It cannot predict every side effect, latency,
  provider failure, or permission error of live integrations.
- `observe` governs an observed execution; it cannot reconstruct events that
  the host never supplied.

## Determinism and replay limits

A stable seed and exact replay policy cannot control nondeterminism outside the
recorded boundary. Provider changes, parallel hardware, wall-clock services,
mutable remote data, unversioned tools, and incomplete environment capture can
still cause divergence. Strict mode is a refusal policy over declared evidence,
not a proof that the universe was deterministic.

Replay detects changes represented in the envelope, fingerprints, events, and
dataset descriptors. It cannot recover deleted external artifacts or compare
state that was never recorded. Human intervention is replayable only when its
decision and relevant input are captured as governed events.

## Verification limits

Runtime verification evaluates registered structural and epistemic rules,
budgets, evidence references, artifact hashes, and arbitration policy. A passing
decision proves those rules passed. It does not certify scientific truth,
legal compliance, model calibration, or the completeness of the rule registry.

Permissive arbitration or verification failure modes are visible policy
choices. Downstream consumers must inspect the arbitration decision and
`non_certifiable` state rather than treating every finalized trace as accepted.

## Persistence limits

DuckDB provides durable local execution state, migrations, and guarded writer
access. It is not a replicated multi-region event store. Host failure during an
external side effect can occur between that effect and its checkpoint; an
integration must provide idempotency when retrying could duplicate work.

Artifact storage and the execution database also require host-level backup,
encryption, retention, access control, and capacity management. Tenant
identifiers in contracts do not replace filesystem or database isolation.

## CLI discoverability

The runtime implements `plan`, `dry-run`, `unsafe-run`, `diff run`,
`explain failure`, `validate db`, and `inspect run`, but several of these are
suppressed from top-level argparse help. They remain callable and tested; users
should consult the command reference rather than assume the visible help list
is the complete interface. The HTTP contract is the primary versioned
integration surface.

## Deployment boundary

The package is not a process sandbox, queue, cluster scheduler, identity
provider, or secret manager. Execute untrusted tools behind operating-system or
container isolation, authorize store access outside the in-process authority
token, and keep credentials out of manifests, traces, replay envelopes, and
artifacts.
