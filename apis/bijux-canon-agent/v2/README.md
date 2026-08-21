# Bijux Canon research-loop artifact contract v2

This contract versions research plans, role transitions, tool and provider
calls, critiques, synthesis, stop decisions, and their causal trace. It also
versions the bounded state needed to resume or audit an agent: current question,
claim graph, evidence gaps, tool permissions, complete resource budgets,
checkpoints, cancellation, provider records, and terminal outcome. Records use
RFC 8785 canonical JSON and SHA-256 identity after removing only the root
`artifact_id`.

Sequences and causal links are explicit. Tool access is default-deny. The
bounded budget covers iterations, retrievals, candidates, evidence, tool and
provider calls, tokens, elapsed time, retries, and artifact bytes. Each state
transition binds a checkpoint, while cancellation and deadlines preserve the
partial evidence needed for inspection or resumption. Provider calls bind
immutable model and prompt/response identities, and terminal state binds one
explicit outcome. Unknown versions and implicit or lossy migrations fail closed
under [`migration-policy.json`](migration-policy.json).
