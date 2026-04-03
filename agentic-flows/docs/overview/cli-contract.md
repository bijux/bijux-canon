# CLI Contract
> Exit code semantics for operator usage.

Exit code 0 means the command completed successfully under declared contracts.
Exit code 1 means the command failed due to a contract violation or runtime failure.
Exit code 2 means the command was invoked incorrectly or with invalid arguments.

## Environment

- `AGENTIC_FLOWS_STRICT=1` forbids best-effort modes and enforces strict determinism.
