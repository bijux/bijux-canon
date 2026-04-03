# Failure semantics

- **InvariantError**: terminal, never retryable; indicates contract or state violation.
- **BudgetExceededError**: execution stops, may return partial results; classified as retryable only if budgets are adjusted.
- **BackendDivergenceError**: indicates drift between backends; requires operator action, not blind retry.
- **ValidationError** / **ConflictError** / **NotFoundError**: client or request issues; retries without change are meaningless.
- **AtomicityViolationError**: transactional misuse; must be fixed in code/tests.
- **NDExecutionUnavailableError**: non-deterministic execution requested without ANN support; allowed failure mode, caller must select a deterministic contract or provide ANN backend.
- **BackendCapabilityError**: requested capability (e.g., external vector store) not available; no silent fallback.
- **AnnIndexBuildError / AnnQueryError / AnnBudgetError**: ANN backend failures are terminal for the request; no silent fallback to exact execution.

Classification lives in `FailureKind` and `FAILURE_ACTIONS`:

- retryable: transient backend or IO failures (not invariants).
- terminal: invariants, ABI mismatches, capability refusals.
- alert/escalate: backend divergence, provenance corruption.

## Error semantics table

| Error type | Retryable | User-visible | Provenance impact | Deterministic outcome |
| --- | --- | --- | --- | --- |
| `InvariantError` | No | Yes | Recorded as terminal failure | Execution aborted |
| `ValidationError` | No | Yes | Recorded | N/A |
| `BudgetExceededError` | No (partial) | Yes | Partial results stored; status PARTIAL | Deterministic: mismatch; ND: allowed with divergence recorded |
| `BackendDivergenceError` | No | Yes | Stored with divergence detail | Deterministic: failure; ND: allowed with bounds |
| `ReplayNotSupportedError` | No | Yes | No new provenance | N/A |
| `AuthzDeniedError` | No | Yes | No execution recorded | N/A |
| `NotFoundError` | No | Yes | No execution recorded | N/A |
| `NDExecutionUnavailableError` | No | Yes | Recorded with capability refusal | N/A |
| `BackendCapabilityError` | No | Yes | Recorded with capability refusal | N/A |
| `AnnIndexBuildError` | No | Yes | Recorded with ANN failure detail | N/A |
| `AnnQueryError` | No | Yes | Recorded with ANN failure detail | N/A |
| `AnnBudgetError` | No | Yes | Recorded with ANN budget detail | N/A |
| Stable public errors | `ValidationError`, `InvariantError`, `ConflictError`, `NotFoundError`, `AuthzDeniedError`, `BackendDivergenceError`, `BackendCapabilityError`, `ReplayNotSupportedError`, `BudgetExceededError`, `AnnIndexBuildError`, `AnnQueryError`, `AnnBudgetError`, `NDExecutionUnavailableError` | | | |

Docs → code

- `src/bijux_vex/core/errors/error_types.py`
- `src/bijux_vex/core/failures.py`
- `src/bijux_vex/domain/provenance/replay.py`
