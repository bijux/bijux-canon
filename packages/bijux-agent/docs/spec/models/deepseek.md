# DeepSeek backend notes

This document captures backend-specific constraints that affect auditability.

## Key point

Providers differ in:

- supported parameters (temperature, max tokens),
- determinism guarantees,
- error modes and rate limits.

The system’s contract is defined in terms of recorded metadata and artifacts, not in terms of provider behavior.

## Practical guidance

- Record `model_metadata` faithfully (provider/model/temperature/max tokens).
- Treat provider errors as operational failures (`execution_error` or `resource_exhaustion`) depending on the failure mode.
- Do not claim replayability when sampling is enabled.
