# Bijux Canon reasoning artifact contract v2

This contract versions scoped questions, bounded evidence packets, grounded
answers, atomic claims, exact citations and claim-citation links, evidence
relations, declared assumptions, insufficiency assessments, conflict
assessments, provider provenance, policy outcomes, confidence calculations, and
verification receipts. Records are closed and use RFC 8785 canonical JSON.
Their `artifact_id` is SHA-256 over the complete canonical record after removing
only the root `artifact_id`.

Citation coordinates select exact bytes or Unicode code points from an admitted
chunk. A verifier recomputes the quoted text and digest; a nearby sentence, a
document-level URL, or an unverified marker is not an exact citation. Evidence
relations explicitly distinguish support, opposition, and ambiguity.

Answered and partial outcomes require atomic claims and verified citation
links. Abstained and refused outcomes cannot expose claims. Provider records
retain bounded attempts and request/response hashes while excluding credentials.
Insufficient evidence packets and verification receipts may be empty; this is
the typed representation for no-hit retrieval and never licenses a citation.

Unknown versions, implicit upgrades, downgrades, and lossy migration fail closed
according to [`migration-policy.json`](migration-policy.json).
