# Failure Semantics

Failures in `bijux-canon-index` are not an implementation detail. They are part
of the package contract because callers and operators need to understand what
went wrong and whether retry, fallback, or investigation makes sense.

## Failure categories

- validation failures: the request or declared contract is invalid before execution starts
- invariant failures: an internal guarantee was violated
- capability failures: the chosen backend or plugin cannot do what was asked
- budget failures: latency, memory, or approximation constraints were exceeded
- replay failures: the package cannot honor the requested reproducibility constraint

## Boundary rule

CLI, HTTP, and stored run records must preserve these meanings instead of
inventing ad-hoc categories or flattening everything into a generic failure.

New failure categories are justified only when downstream tooling or operators
can act differently because of the distinction.
