# Execution intent contract matrix

| intent                | allowed contracts         | allowed modes            |
| --------------------- | ------------------------- | ------------------------ |
| EXACT_VALIDATION      | deterministic             | strict                   |
| REPRODUCIBLE_RESEARCH | deterministic, non_deterministic | strict (DET), bounded/ exploratory (ND) |
| EXPLORATORY_SEARCH    | non_deterministic         | bounded, exploratory     |
| PRODUCTION_RETRIEVAL  | deterministic             | strict                   |

Rules:

- Intent is always explicit and coerced to `ExecutionIntent` at boundary ingress.
- Non-deterministic intents require an execution budget and randomness profile.
- Deterministic intents must use strict mode; ND intents must not use strict mode.
