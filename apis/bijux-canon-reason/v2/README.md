# Bijux Canon reasoning artifact contract v2

This contract versions atomic claims, exact citations, evidence relations,
declared assumptions, insufficiency assessments, confidence calculations, and
verification receipts. Records are closed and use RFC 8785 canonical JSON.
Their `artifact_id` is SHA-256 over the complete canonical record after removing
only the root `artifact_id`.

Citation coordinates select exact bytes or Unicode code points from an admitted
chunk. A verifier recomputes the quoted text and digest; a nearby sentence, a
document-level URL, or an unverified marker is not an exact citation. Evidence
relations explicitly distinguish support, opposition, and ambiguity.

Unknown versions, implicit upgrades, downgrades, and lossy migration fail closed
according to [`migration-policy.json`](migration-policy.json).
