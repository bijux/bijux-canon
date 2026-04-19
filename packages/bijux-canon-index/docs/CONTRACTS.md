# Contracts

The contract surface of `bijux-canon-index` includes more than HTTP schemas.

## Stable surfaces

- API schemas under `apis/03-bijux-canon-index/v1/`
- plugin entrypoint groups for vector stores, embeddings, and runners
- public HTTP behavior under `src/bijux_canon_index/api/v1/`
- stable models and typed failures under `core/` and boundary schemas

## Change policy

- schema changes must be intentional and reviewed as contract changes
- plugin contracts must stay explicit enough that third-party or internal plugins know what to implement
- failure meanings should not drift just because backend behavior changed

The package does not currently publish a primary console script. Treat CLI code
as operator tooling unless the package explicitly promotes it as a supported surface.
