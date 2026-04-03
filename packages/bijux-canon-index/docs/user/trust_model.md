# Trust Model & Guarantees

Bijux-Vex separates **hard guarantees** from **best-effort behavior**. When a guarantee cannot be met, the system refuses instead of guessing.

Hard guarantees

- Deterministic execution is exact, replayable, and stable.
- Canonical ordering rules apply to deterministic results.
- Provenance is always emitted for executed requests.
- Refusals are explicit and structured.

Best-effort behavior

- ND quality depends on the selected runner, parameters, and index state.
- ND witness verification is optional and may be partial.
- Backend availability and performance depend on external systems.

Not guaranteed

- Cross-backend numeric equivalence beyond the defined query contract.
- Near-zero latency for ND under heavy load.
- Implicit retries or silent fallbacks when backends fail.

How refusal protects correctness

- If a backend lacks required capabilities, the system refuses.
- If ND cannot honor replay or determinism bounds, the system refuses.
- If budgets would be exceeded, the system refuses rather than degrade silently.

This trust model is designed so teams can **approve adoption** without hidden behavior.
