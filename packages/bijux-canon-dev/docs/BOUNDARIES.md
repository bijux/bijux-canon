# BOUNDARIES

`bijux-canon-dev` owns repository automation that should not live inside product packages.

It does own:
- shared quality, security, SBOM, release, and OpenAPI helpers
- package-specific maintenance checks used by root automation
- tooling invoked by `make`, CI, and packaging flows

It does not own:
- end-user product behavior
- long-lived domain models from runtime, agent, ingest, index, or reason
- application-specific workflows
