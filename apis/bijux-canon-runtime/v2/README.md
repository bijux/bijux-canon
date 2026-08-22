# Bijux Canon runtime-run artifact contract v2

This contract versions immutable runtime DAGs, policies, jobs, step attempts,
produced artifacts, events, inspections, cancellation decisions, replay results,
comparisons, and publication receipts. Records use RFC 8785 canonical JSON and
SHA-256 identity after removing only the root `artifact_id`.

The semantic `run_key` binds immutable inputs independently of process IDs and
timestamps. Attempts are append-only, payloads use content-addressed storage,
and publication fails closed unless inspection, replay, comparison, and required
checks pass. Unknown versions and implicit or lossy migrations fail closed under
[`migration-policy.json`](migration-policy.json).

The DAG contract assigns exactly one operation to every node: ingest, snapshot,
embed, lexical index, dense index, retrieve, reason, agent, verify, persist, or
publish. Every node declares content-addressed input and output artifact
contracts. Each edge names the exact output contract transferred to its consumer,
so an executor can reject unresolved nodes, cycles, contract mismatches, and
compound implicit work before starting a run.
