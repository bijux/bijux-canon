# v0.2.0 Progress Checklist

This checklist maps tasks to phases. It is the release gate for v0.2.0.

## Phase A — Contract & Compatibility Guardrails
- [ ] Backward compatibility contract doc
- [ ] Golden v0.1 replay test
- [ ] CLI flags snapshot test
- [ ] Implicitness contract doc
- [ ] Capabilities report command

## Phase B — Vector DB Architecture (Design First)
- [ ] VectorStoreAdapter interface (code + doc)
- [ ] Explicit opt-in flag design doc
- [ ] Determinism matrix (storage × execution)
- [ ] Failure semantics spec updates
- [ ] Architecture diagram update

## Phase C — Embeddings & ANN Guardrails
- [ ] Embedding generation contract doc
- [ ] Provenance schema extension
- [ ] ANN graduation criteria
- [ ] ANN runner audit doc
- [ ] Performance baseline harness + stored results

## Phase D — Docs, UX, Trust
- [ ] README ↔ docs drift fixed
- [ ] “Not a Vector DB” section rewritten
- [ ] Start Here path added
- [ ] Experimental labels everywhere
- [ ] v0.2.0 checklist published
