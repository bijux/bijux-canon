# System boundaries (maintainer)

Bijux Agent is a pipeline runner with strict audit artifacts. Keeping the boundary sharp is how the project stays maintainable.

## Inside the boundary

- construct a context
- run the canonical pipeline
- record trace and final artifacts
- expose a minimal API surface

## Outside the boundary

- long-lived storage and user accounts
- permission systems and multi-tenant isolation
- UI and product workflows
- domain-specific “correctness” definitions

If a feature drags the project toward “application platform”, resist it unless it directly strengthens auditability.
