# Mental Model

`bijux-canon-index` is an execution package, not a generic vector database.

The package accepts declared execution intent, runs that intent against a
specific backend or artifact, and returns results together with enough context
to answer the follow-up questions a serious system always has:

- which backend produced this result
- what capabilities and limits were in play
- how reproducible was the execution
- what changed when we compared or replayed it later

## Keep these roles in mind

- `core` defines durable types and package-wide primitives
- `domain` defines the meaning of execution, scoring, replay, and drift
- `application` turns those rules into package workflows
- `infra` does the real backend and plugin work
- `interfaces` shapes requests and responses for callers

The package is successful when maintainers can explain not just "what matched,"
but also "why that answer is trustworthy under this contract."
