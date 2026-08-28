# Independent annotation protocol

Evaluation truth is authored from admitted source material before anyone inspects the system output for the case. The annotation workflow binds every decision to the SHA-256 identity of this protocol and to an immutable truth revision. A changed label, locator, rationale, or expectation creates a new revision linked to its predecessor; it never overwrites an admitted revision.

## Source-first procedure

1. Freeze the case identifier, development or held-out split, source identities, and exact evidence locators.
2. Author atomic expected, optional, opposed, and forbidden claims from those sources. Record conflict and abstention expectations explicitly.
3. Record a revision with the author, date, protocol identity, and previous revision identity. The author must confirm that source material was reviewed and system output was not consulted.
4. Assign the revision to reviewers who are distinct from the author and from one another. Reviewers inspect the same frozen sources and record a rationale plus every concrete conflict.
5. Require at least two independent reviewers for held-out truth. Development truth may be admitted after one independent approval.
6. When reviewers disagree, request changes, or record conflicts, use an adjudicator who is not one of the reviewers. The adjudication must reference all selected reviews and resolve the exact conflict set.
7. Admit only a unanimous conflict-free approval or an explicit admitting adjudication. A rejected adjudication remains evidence but cannot become evaluation truth.

## Independence rules

System answers, rankings, claims, citations, traces, scores, and model-generated labels are prohibited annotation inputs. They cannot define truth, suggest missing labels, choose easier cases, or resolve disagreements. Source-first confirmation is a typed constant on revisions, reviews, and adjudications; records that claim otherwise are rejected before admission.

Review identities are pseudonymous stable operator identifiers. The workflow requires distinct reviewers and rejects self-review. Held-out adjudicators must also be independent of the selected reviewers.

## Revision and conflict handling

Revision identity is the SHA-256 digest of canonical JSON for the complete frozen revision. Each successor stores its immediate predecessor digest. The workflow rejects gaps, forks presented as a linear history, duplicate revision identifiers, mixed cases, or records bound to another protocol.

A conflict record names the affected subject and explains the disagreement. Approving reviews cannot retain conflicts. Adjudication must account for exactly the union of conflicts recorded by the selected reviews: unresolved conflicts and invented resolutions both fail admission.

## Held-out isolation

Held-out labels are unavailable to prompts, tuning, reranking, thresholds, case selection, or development diagnostics. Only the admitted revision identity and admission record enter evaluation execution. Reports may publish aggregate held-out results and required per-case audit records after the evaluation is frozen; they must not turn held-out truth into development input.

## Audit record

An admitted case retains the case and split, protocol digest, selected revision digest, review and reviewer identifiers, adjudication identifier when used, and resolved conflict identifiers. The admission is itself content-addressed. These identities allow an auditor to reproduce the decision chain without relying on a mutable path or a current working copy.
