# Agent contract (spec)

Agents are *workers*. They do not orchestrate execution.

## Responsibilities

Agents MAY:

- read/transform text
- produce structured artifacts
- emit confidence scores

Agents MUST NOT:

- manage pipeline lifecycle or transitions
- persist state across runs (unless explicitly designed and documented)
- write final artifacts directly (that is `FINALIZE` responsibility)

## Input contract

Every agent run should be representable as an `AgentInputSchema`:

- `task_goal` (string)
- `context_id` (string)
- `payload` (mapping)
- `metadata` (mapping)

## Output contract

Agent outputs must satisfy `AgentOutputSchema`:

- `text` (non-empty)
- `confidence` in `[0, 1]`
- `metadata.contract_version` matching the runtime contract version

This strictness is deliberate: it keeps downstream decisions stable even as prompts or models evolve.

(Implementation reference: `src/bijux_agent/models/contract.py`.)
