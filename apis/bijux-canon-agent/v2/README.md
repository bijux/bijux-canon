# Bijux Canon research-loop artifact contract v2

This contract versions research plans, role transitions, tool and provider
calls, budgets, critiques, synthesis, stop decisions, and their causal trace.
Records use RFC 8785 canonical JSON and SHA-256 identity after removing only the
root `artifact_id`.

Sequences and causal links are explicit. Budgets bind limits and usage, provider
calls bind immutable model and prompt/response identities, and every terminal
decision identifies the policy and synthesis that caused it. Unknown versions
and implicit or lossy migrations fail closed under
[`migration-policy.json`](migration-policy.json).
