# Implicitness Contract (Nothing Is Implicit)

bijux-vex forbids silent behavior. Any decision that can change results, persistence, or replayability must be **explicit** in the request or configuration.

## What counts as implicit behavior
The following are **not allowed** without an explicit flag or field:

- Choosing a deterministic vs non-deterministic execution contract.
- Switching to approximate/ANN execution or falling back to exact execution.
- Persisting vectors or artifacts to any external store.
- Selecting or mutating execution budgets or randomness bounds.
- Injecting embeddings or transforming vectors.
- Replaying against a different plan, ABI, or artifact without a declared contract.

## What is allowed only via explicit flags or fields
The following behaviors must be **opt-in**, never default:

- Vector store selection (e.g., `--vector-store <name>`).
- ANN execution (must declare contract, intent, mode, randomness profile, and budgets).
- Persistence outside the local execution ledger.
- Any embedding generation or model selection.

## Enforcement rules
- If a required flag/field is missing, the system **refuses to run**.
- There is **no silent fallback** (e.g., ANN → exact or VDB → memory).
- Deterministic execution must be strict; non-deterministic execution must be bounded or exploratory.

This contract is normative: future features (VDB integration, embeddings, ANN upgrades) must pass this rule or be rejected.
