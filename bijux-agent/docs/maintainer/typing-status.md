# Typing status (maintainer)

Typing is treated as a correctness tool, not as decoration.

## Policy

- New modules should be typed.
- Contract-relevant modules (trace schema, failure artifacts, API schemas) SHOULD be fully typed.
- Avoid “type: ignore” unless you can explain why it is safe.

## Practical expectation

If mypy coverage is incomplete, focus typing effort where it reduces runtime ambiguity:

- schemas and validation
- artifact writing
- boundary layers (CLI/API)
