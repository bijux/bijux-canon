# EFFECTS

`bijux-canon-index` performs these important effects:
- connects to vector stores and embedding providers
- persists run and artifact state through infra adapters
- loads plugins through entrypoint discovery
- emits API schemas and benchmark artifacts

Effectful behavior belongs in `infra/`, `application/`, and `interfaces/`, not inside stable core models.
