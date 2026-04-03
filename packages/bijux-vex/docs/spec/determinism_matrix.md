# Determinism Matrix (Storage × Execution)

This matrix is normative. It defines determinism, auditability, and experimental status for each storage/execution combination.

| Storage | Execution | Deterministic? | Auditable? | Experimental? | Notes |
| --- | --- | --- | --- | --- | --- |
| Memory | Exact | Yes | Yes | No | Fully deterministic; replay must match bit-for-bit. |
| Memory | ANN | No (bounded) | Yes | Yes | Requires randomness profile + budgets; replay is envelope-based. |
| VDB (FAISS local) | Exact | Yes | Yes | Yes | IndexFlatL2 is deterministic; explicit opt-in required. |
| VDB (FAISS local) | ANN | No (bounded) | Only if adapter proves it | Yes | ANN not implemented in v0.2. |
| VDB (external) | Exact | No by default | Only if adapter proves it | Yes (future) | Requires explicit opt-in + adapter contract. |
| VDB (external) | ANN | No (bounded) | Only if adapter proves it | Yes (future) | Explicit opt-in required. |

## Determinism rules
- “Deterministic” means **bit-identical replay** under the same contract.
- “Auditable” means provenance is emitted and replay/compare are legal under declared bounds.
- Any VDB path is **non-default** and must be explicitly selected.
