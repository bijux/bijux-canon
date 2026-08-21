# Parser qualification sources

This portfolio defines the seven real documents used to qualify the ingestion
adapters. It is deliberately separate from the ancient-DNA research corpus:
these documents establish parser and locator behavior, not research relevance.

`sources.jsonl` is the durable source policy. Each line records canonical
metadata, an exact acquisition endpoint, license evidence, redistribution
terms, format-specific admission requirements, and the independent locator
truth that must be authored before admission. The source bytes, acquisition
receipts, byte lock, and locator truth are added only after their corresponding
reviews succeed.

Generated download logs and verification evidence are disposable and remain
under the ignored repository `artifacts/` directory. They are never source
inputs and are never tracked by Git.
