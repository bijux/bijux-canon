# Docstring policy (maintainer)

Docstrings are not a dumping ground for design documents. They exist to make code easier to use and harder to misuse.

## Required

- Public functions/classes MUST have docstrings describing purpose and key constraints.
- Contract-relevant types (trace schema, failure artifacts) SHOULD have docstrings that match the spec vocabulary.

## Avoid

- Repeating spec text verbatim.
- Describing behavior that tests do not enforce.
- Encoding large examples in docstrings (prefer docs pages for that).

If a docstring becomes the “source of truth”, the docs are already drifting.
