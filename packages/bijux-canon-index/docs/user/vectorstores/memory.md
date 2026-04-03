# Memory Vector Store

## Install

- No extras required.

## Connect

Memory is the default when no `--vector-store` is provided.

## Capabilities

- Exact search only.
- Ephemeral (no persistence).

## Limitations

- Data is lost when the process exits.
- Not suitable for large corpora.

## Recommended Use Cases

- Local testing and CI.
- Deterministic exact validation.

## Gotchas

- No persistence. Replay across restarts is not possible.
