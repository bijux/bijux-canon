# API Error Model (v1)

Errors are explicit, typed, and mapped to HTTP and retry semantics.

- `ValidationError` → 400, not retryable
- `InvariantError` → 422, terminal
- `BackendCapabilityError` → 422, fix configuration
- `AuthzDeniedError` → 403
- `ConflictError` / `AtomicityViolationError` → 409
- `AnnIndexBuildError` / `AnnQueryError` → 500
- `AnnBudgetError` / `BudgetExceededError` → 422, not retryable
- `ReplayNotSupportedError` → 422
- All errors carry invariant IDs where applicable.

Clients should not rely on string matching; use status codes and error type names. Retries are only allowed when errors are explicitly marked retryable in the payload or classification tests.
