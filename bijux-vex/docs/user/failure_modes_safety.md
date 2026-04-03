# Failure Modes & Safety

Atomicity guarantees

- Ingest and artifact writes are atomic when possible.
- Partial writes are refused and marked incomplete.

Crashes

- Incomplete runs are marked as invalid and excluded from replay or compare.

Partial failures

- Remote backends use explicit retry policies.
- Partial batch failures are detected and surfaced.

Circuit breakers

- Repeated ND backend failures trigger fast refusal.
- Cooldown is explicit and visible in capabilities.

Idempotency

- Ingest supports idempotency keys for safe retries.
- Duplicate detection is explicit and refuses when conflicting.

Example scenario

- If a remote upsert times out mid-batch, the retry policy is applied.
- If duplicates are detected, the system refuses with a remediation message.
