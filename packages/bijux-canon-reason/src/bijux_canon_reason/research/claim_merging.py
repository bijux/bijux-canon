# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Canonicalize equivalent research claims without losing scope or lineage."""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class ClaimMergeErrorCode(StrEnum):
    """Stable failures that prevent safe canonicalization."""

    duplicate_claim = "duplicate_claim"
    unknown_dependency = "unknown_dependency"
    self_dependency = "self_dependency"
    source_dependency_cycle = "source_dependency_cycle"
    canonical_dependency_cycle = "canonical_dependency_cycle"


class ClaimMergeError(ValueError):
    """Claims cannot be merged without losing graph integrity."""

    def __init__(self, code: ClaimMergeErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class ClaimQualification(StableModel):
    """Exact scope and named qualifiers that must survive semantic merging."""

    scope_artifact_id: str
    qualifiers: tuple[tuple[str, str], ...] = ()

    @field_validator("scope_artifact_id")
    @classmethod
    def _validate_scope(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("qualifiers")
    @classmethod
    def _validate_qualifiers(
        cls, value: tuple[tuple[str, str], ...]
    ) -> tuple[tuple[str, str], ...]:
        normalized = tuple(
            (" ".join(name.split()), " ".join(item.split())) for name, item in value
        )
        names = tuple(name for name, _ in normalized)
        if any(not name or not item for name, item in normalized) or len(names) != len(
            set(names)
        ):
            raise ValueError(
                "claim qualifiers require unique non-empty names and values"
            )
        return tuple(sorted(normalized))


class MergeableClaim(StableModel):
    """One source claim with explicit semantic identity and exact evidence."""

    claim_artifact_id: str
    proposition_artifact_id: str
    statement: str
    qualification: ClaimQualification
    evidence_artifact_ids: tuple[str, ...]
    derived_from_claim_artifact_ids: tuple[str, ...] = ()

    @field_validator("claim_artifact_id", "proposition_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("statement")
    @classmethod
    def _validate_statement(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("mergeable claims require a statement")
        return normalized

    @field_validator("evidence_artifact_ids", "derived_from_claim_artifact_ids")
    @classmethod
    def _validate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("claim evidence and dependency identities must be unique")
        return tuple(sorted(require_artifact_id(item) for item in value))


class CanonicalClaimVariant(StableModel):
    """Equivalent claim wording under one exact qualification boundary."""

    artifact_id: str
    qualification: ClaimQualification
    statements: tuple[str, ...]
    source_claim_artifact_ids: tuple[str, ...]
    evidence_artifact_ids: tuple[str, ...]

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("source_claim_artifact_ids")
    @classmethod
    def _validate_source_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("canonical variants require unique source claims")
        return tuple(require_artifact_id(item) for item in value)

    @field_validator("evidence_artifact_ids")
    @classmethod
    def _validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("canonical variant evidence must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_variant(self) -> Self:
        if (
            not self.statements
            or tuple(sorted(set(self.statements))) != self.statements
        ):
            raise ValueError("canonical variant statements must be unique and sorted")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("canonical claim variant identity does not match")
        return self


class CanonicalResearchClaim(StableModel):
    """One semantic proposition with all qualification variants and unique evidence."""

    artifact_id: str
    graph_artifact_id: str
    proposition_artifact_id: str
    preferred_statement: str
    variants: tuple[CanonicalClaimVariant, ...]
    source_claim_artifact_ids: tuple[str, ...]
    evidence_artifact_ids: tuple[str, ...]
    unique_support_count: int

    @field_validator("artifact_id", "graph_artifact_id", "proposition_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("source_claim_artifact_ids")
    @classmethod
    def _validate_source_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("canonical claims require unique source claims")
        return tuple(require_artifact_id(item) for item in value)

    @field_validator("evidence_artifact_ids")
    @classmethod
    def _validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("canonical claim evidence must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_claim(self) -> Self:
        if not self.variants or not self.preferred_statement:
            raise ValueError("canonical claims require variants and preferred wording")
        variant_sources = {
            item
            for variant in self.variants
            for item in variant.source_claim_artifact_ids
        }
        variant_evidence = {
            item for variant in self.variants for item in variant.evidence_artifact_ids
        }
        if variant_sources != set(self.source_claim_artifact_ids):
            raise ValueError("canonical claim sources must equal its variant sources")
        if variant_evidence != set(self.evidence_artifact_ids):
            raise ValueError("canonical claim evidence must equal its variant evidence")
        if self.unique_support_count != len(self.evidence_artifact_ids):
            raise ValueError("canonical support count must use unique evidence")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("canonical research claim identity does not match")
        return self


class ClaimCanonicalization(StableModel):
    """Exact source-claim mapping into a canonical claim and variant."""

    source_claim_artifact_id: str
    canonical_claim_artifact_id: str
    variant_artifact_id: str

    @field_validator(
        "source_claim_artifact_id", "canonical_claim_artifact_id", "variant_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)


class CanonicalDerivationDependency(StableModel):
    """Canonical dependency retaining all exact source dependency pairs."""

    artifact_id: str
    parent_canonical_claim_artifact_id: str
    child_canonical_claim_artifact_id: str
    source_dependency_pairs: tuple[tuple[str, str], ...]
    internal_to_canonical_claim: bool

    @field_validator(
        "artifact_id",
        "parent_canonical_claim_artifact_id",
        "child_canonical_claim_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_dependency(self) -> Self:
        if not self.source_dependency_pairs:
            raise ValueError("canonical dependencies require source lineage")
        for parent, child in self.source_dependency_pairs:
            require_artifact_id(parent)
            require_artifact_id(child)
        if (
            tuple(sorted(set(self.source_dependency_pairs)))
            != self.source_dependency_pairs
        ):
            raise ValueError("source dependency pairs must be unique and sorted")
        same = (
            self.parent_canonical_claim_artifact_id
            == self.child_canonical_claim_artifact_id
        )
        if same != self.internal_to_canonical_claim:
            raise ValueError(
                "internal dependency status must match canonical endpoints"
            )
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("canonical dependency identity does not match")
        return self


class SharedEvidenceUse(StableModel):
    """One evidence identity used by multiple canonical claims without recounting."""

    evidence_artifact_id: str
    canonical_claim_artifact_ids: tuple[str, ...]
    source_claim_artifact_ids: tuple[str, ...]

    @field_validator(
        "evidence_artifact_id",
        "canonical_claim_artifact_ids",
        "source_claim_artifact_ids",
    )
    @classmethod
    def _validate_ids(cls, value: str | tuple[str, ...]) -> str | tuple[str, ...]:
        if isinstance(value, str):
            return require_artifact_id(value)
        if len(value) < 2 or len(value) != len(set(value)):
            raise ValueError("shared evidence must identify at least two unique uses")
        return tuple(require_artifact_id(item) for item in value)


class ClaimMergeResult(StableModel):
    """Closed canonical claim graph with deduplicated support accounting."""

    schema_version: Literal["bijux.canon.reason.claim_merge_result.v1"] = (
        "bijux.canon.reason.claim_merge_result.v1"
    )
    artifact_id: str
    graph_artifact_id: str
    canonical_claims: tuple[CanonicalResearchClaim, ...]
    mappings: tuple[ClaimCanonicalization, ...]
    dependencies: tuple[CanonicalDerivationDependency, ...]
    shared_evidence: tuple[SharedEvidenceUse, ...]
    unique_evidence_artifact_ids: tuple[str, ...]
    raw_evidence_reference_count: int
    prevented_double_count: int

    @field_validator("artifact_id", "graph_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("unique_evidence_artifact_ids")
    @classmethod
    def _validate_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("merged evidence identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_result(self) -> Self:
        if self.raw_evidence_reference_count < len(self.unique_evidence_artifact_ids):
            raise ValueError("raw evidence references cannot be below unique evidence")
        if self.prevented_double_count != (
            self.raw_evidence_reference_count - len(self.unique_evidence_artifact_ids)
        ):
            raise ValueError("prevented double count must match evidence cardinality")
        if len(self.mappings) != len(
            {item.source_claim_artifact_id for item in self.mappings}
        ):
            raise ValueError("each source claim must map exactly once")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("claim merge result identity does not match")
        return self


class ClaimMergingService:
    """Merge only explicitly equivalent propositions and retain graph distinctions."""

    def merge(
        self, *, graph_artifact_id: str, claims: tuple[MergeableClaim, ...]
    ) -> ClaimMergeResult:
        """Canonicalize claims deterministically and reject dependency cycles."""

        require_artifact_id(graph_artifact_id)
        claim_ids = tuple(item.claim_artifact_id for item in claims)
        if len(claim_ids) != len(set(claim_ids)):
            raise ClaimMergeError(
                ClaimMergeErrorCode.duplicate_claim,
                "source claim identities must be unique",
            )
        known = set(claim_ids)
        for claim in claims:
            for parent in claim.derived_from_claim_artifact_ids:
                if parent not in known:
                    raise ClaimMergeError(
                        ClaimMergeErrorCode.unknown_dependency,
                        "claim derivation references an unknown parent",
                    )
                if parent == claim.claim_artifact_id:
                    raise ClaimMergeError(
                        ClaimMergeErrorCode.self_dependency,
                        "a claim cannot derive from itself",
                    )
        source_edges = tuple(
            (parent, claim.claim_artifact_id)
            for claim in claims
            for parent in claim.derived_from_claim_artifact_ids
        )
        _assert_acyclic(
            known, source_edges, ClaimMergeErrorCode.source_dependency_cycle
        )

        grouped: dict[str, list[MergeableClaim]] = defaultdict(list)
        for claim in claims:
            grouped[claim.proposition_artifact_id].append(claim)
        canonical_claims = tuple(
            _canonical_claim(graph_artifact_id, proposition, tuple(group))
            for proposition, group in sorted(grouped.items())
        )
        source_to_canonical: dict[str, tuple[str, str]] = {}
        mappings = []
        for canonical in canonical_claims:
            for variant in canonical.variants:
                for source_id in variant.source_claim_artifact_ids:
                    source_to_canonical[source_id] = (
                        canonical.artifact_id,
                        variant.artifact_id,
                    )
                    mappings.append(
                        ClaimCanonicalization(
                            source_claim_artifact_id=source_id,
                            canonical_claim_artifact_id=canonical.artifact_id,
                            variant_artifact_id=variant.artifact_id,
                        )
                    )
        dependencies = _canonical_dependencies(source_edges, source_to_canonical)
        canonical_edges = tuple(
            (
                item.parent_canonical_claim_artifact_id,
                item.child_canonical_claim_artifact_id,
            )
            for item in dependencies
            if not item.internal_to_canonical_claim
        )
        _assert_acyclic(
            {item.artifact_id for item in canonical_claims},
            canonical_edges,
            ClaimMergeErrorCode.canonical_dependency_cycle,
        )
        shared = _shared_evidence(claims, source_to_canonical)
        unique_evidence = tuple(
            sorted({item for claim in claims for item in claim.evidence_artifact_ids})
        )
        raw_count = sum(len(item.evidence_artifact_ids) for item in claims)
        ordered_mappings = tuple(
            sorted(mappings, key=lambda item: item.source_claim_artifact_id)
        )
        payload = {
            "schema_version": "bijux.canon.reason.claim_merge_result.v1",
            "graph_artifact_id": graph_artifact_id,
            "canonical_claims": tuple(
                item.model_dump(mode="json") for item in canonical_claims
            ),
            "mappings": tuple(
                item.model_dump(mode="json") for item in ordered_mappings
            ),
            "dependencies": tuple(
                item.model_dump(mode="json") for item in dependencies
            ),
            "shared_evidence": tuple(item.model_dump(mode="json") for item in shared),
            "unique_evidence_artifact_ids": unique_evidence,
            "raw_evidence_reference_count": raw_count,
            "prevented_double_count": raw_count - len(unique_evidence),
        }
        return ClaimMergeResult(
            artifact_id=content_artifact_id(payload),
            graph_artifact_id=graph_artifact_id,
            canonical_claims=canonical_claims,
            mappings=ordered_mappings,
            dependencies=dependencies,
            shared_evidence=shared,
            unique_evidence_artifact_ids=unique_evidence,
            raw_evidence_reference_count=raw_count,
            prevented_double_count=raw_count - len(unique_evidence),
        )


def create_mergeable_claim(
    *,
    claim_artifact_id: str,
    semantic_key: str,
    statement: str,
    scope_artifact_id: str,
    qualifiers: tuple[tuple[str, str], ...] = (),
    evidence_artifact_ids: tuple[str, ...],
    derived_from_claim_artifact_ids: tuple[str, ...] = (),
) -> MergeableClaim:
    """Create an explicitly keyed claim without inferring equivalence from overlap."""

    normalized_key = " ".join(semantic_key.casefold().split())
    if not normalized_key:
        raise ValueError("claim semantic keys must not be empty")
    return MergeableClaim(
        claim_artifact_id=claim_artifact_id,
        proposition_artifact_id=content_artifact_id(
            {"semantic_proposition_key": normalized_key}
        ),
        statement=" ".join(statement.split()),
        qualification=ClaimQualification(
            scope_artifact_id=scope_artifact_id,
            qualifiers=qualifiers,
        ),
        evidence_artifact_ids=tuple(sorted(evidence_artifact_ids)),
        derived_from_claim_artifact_ids=tuple(sorted(derived_from_claim_artifact_ids)),
    )


def _canonical_claim(
    graph_id: str, proposition_id: str, claims: tuple[MergeableClaim, ...]
) -> CanonicalResearchClaim:
    by_qualification: dict[str, list[MergeableClaim]] = defaultdict(list)
    for claim in claims:
        key = content_artifact_id(claim.qualification.model_dump(mode="json"))
        by_qualification[key].append(claim)
    variants = []
    for _, group in sorted(by_qualification.items()):
        qualification = group[0].qualification
        variant_statements = tuple(sorted({item.statement for item in group}))
        variant_source_ids = tuple(sorted(item.claim_artifact_id for item in group))
        variant_evidence_ids = tuple(
            sorted(
                {evidence for item in group for evidence in item.evidence_artifact_ids}
            )
        )
        payload = {
            "qualification": qualification.model_dump(mode="json"),
            "statements": variant_statements,
            "source_claim_artifact_ids": variant_source_ids,
            "evidence_artifact_ids": variant_evidence_ids,
        }
        variants.append(
            CanonicalClaimVariant(
                artifact_id=content_artifact_id(payload),
                qualification=qualification,
                statements=variant_statements,
                source_claim_artifact_ids=variant_source_ids,
                evidence_artifact_ids=variant_evidence_ids,
            )
        )
    ordered_variants = tuple(sorted(variants, key=lambda item: item.artifact_id))
    canonical_statements = {item.statement for item in claims}
    preferred = min(canonical_statements, key=lambda item: (len(item), item))
    canonical_source_ids = tuple(sorted(item.claim_artifact_id for item in claims))
    canonical_evidence_ids = tuple(
        sorted({evidence for item in claims for evidence in item.evidence_artifact_ids})
    )
    canonical_payload: dict[str, object] = {
        "graph_artifact_id": graph_id,
        "proposition_artifact_id": proposition_id,
        "preferred_statement": preferred,
        "variants": tuple(item.model_dump(mode="json") for item in ordered_variants),
        "source_claim_artifact_ids": canonical_source_ids,
        "evidence_artifact_ids": canonical_evidence_ids,
        "unique_support_count": len(canonical_evidence_ids),
    }
    return CanonicalResearchClaim(
        artifact_id=content_artifact_id(canonical_payload),
        graph_artifact_id=graph_id,
        proposition_artifact_id=proposition_id,
        preferred_statement=preferred,
        variants=ordered_variants,
        source_claim_artifact_ids=canonical_source_ids,
        evidence_artifact_ids=canonical_evidence_ids,
        unique_support_count=len(canonical_evidence_ids),
    )


def _canonical_dependencies(
    source_edges: tuple[tuple[str, str], ...],
    mapping: dict[str, tuple[str, str]],
) -> tuple[CanonicalDerivationDependency, ...]:
    grouped: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for parent, child in source_edges:
        grouped[(mapping[parent][0], mapping[child][0])].append((parent, child))
    result = []
    for (parent, child), pairs in sorted(grouped.items()):
        ordered_pairs = tuple(sorted(set(pairs)))
        payload = {
            "parent_canonical_claim_artifact_id": parent,
            "child_canonical_claim_artifact_id": child,
            "source_dependency_pairs": ordered_pairs,
            "internal_to_canonical_claim": parent == child,
        }
        result.append(
            CanonicalDerivationDependency(
                artifact_id=content_artifact_id(payload),
                parent_canonical_claim_artifact_id=parent,
                child_canonical_claim_artifact_id=child,
                source_dependency_pairs=ordered_pairs,
                internal_to_canonical_claim=parent == child,
            )
        )
    return tuple(result)


def _shared_evidence(
    claims: tuple[MergeableClaim, ...], mapping: dict[str, tuple[str, str]]
) -> tuple[SharedEvidenceUse, ...]:
    uses: dict[str, list[str]] = defaultdict(list)
    for claim in claims:
        for evidence in claim.evidence_artifact_ids:
            uses[evidence].append(claim.claim_artifact_id)
    result = []
    for evidence, source_ids in sorted(uses.items()):
        canonical_ids = tuple(sorted({mapping[item][0] for item in source_ids}))
        ordered_sources = tuple(sorted(set(source_ids)))
        if len(canonical_ids) < 2:
            continue
        result.append(
            SharedEvidenceUse(
                evidence_artifact_id=evidence,
                canonical_claim_artifact_ids=canonical_ids,
                source_claim_artifact_ids=ordered_sources,
            )
        )
    return tuple(result)


def _assert_acyclic(
    nodes: set[str],
    edges: tuple[tuple[str, str], ...],
    code: ClaimMergeErrorCode,
) -> None:
    children: dict[str, set[str]] = {item: set() for item in nodes}
    indegree = dict.fromkeys(nodes, 0)
    for parent, child in set(edges):
        if child not in children[parent]:
            children[parent].add(child)
            indegree[child] += 1
    ready = sorted(item for item, degree in indegree.items() if degree == 0)
    visited = 0
    while ready:
        node = ready.pop(0)
        visited += 1
        for child in sorted(children[node]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if visited != len(nodes):
        raise ClaimMergeError(code, "claim derivation dependencies must remain acyclic")


__all__ = [
    "CanonicalClaimVariant",
    "CanonicalDerivationDependency",
    "CanonicalResearchClaim",
    "ClaimCanonicalization",
    "ClaimMergeError",
    "ClaimMergeErrorCode",
    "ClaimMergeResult",
    "ClaimMergingService",
    "ClaimQualification",
    "MergeableClaim",
    "SharedEvidenceUse",
    "create_mergeable_claim",
]
