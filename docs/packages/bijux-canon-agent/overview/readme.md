# Documentation orientation

The docs are organized by audience:

- **User**: installation, CLI, output artifacts.
- **Overview**: mental model and vocabulary (explanatory).
- **Reference (Spec)**: test-backed runtime contract (normative).
- **Maintainer**: repo hygiene, refactor guardrails, contributor workflow.

## Normative language

In the **Spec**, the words **MUST**, **SHOULD**, and **MAY** are used in the RFC sense:

- **MUST**: required for correctness and for contract/invariant tests
- **SHOULD**: strong recommendation; deviating requires an explicit reason
- **MAY**: optional behavior

Outside the spec, text is explanatory: it aims to help you use the system, not to bind it.
