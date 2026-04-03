# CLI exit codes

The CLI is part of the public surface. Exit codes are intentional and stable:

- `0`: success.
- `2`: validation or invariant failure (misuse, contract violation).
- `3`: backend capability or availability failure (e.g., ND without ANN).
- `4`: budget exhaustion or policy refusal.
- `1`: unexpected internal error (treated as a bug).

There are no silent retries or fallbacks; failures are terminal and mapped to the nearest code above.
