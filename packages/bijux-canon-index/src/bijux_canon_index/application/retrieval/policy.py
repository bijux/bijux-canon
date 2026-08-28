# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Versioned hybrid-retrieval policies owned by the canonical Index package."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

from ..vex import VexExecutionBudget
from .evidence_planning import EVIDENCE_PLANNING_POLICY_ID
from .fusion import RrfFusionPolicy
from .planned_reranking import PlannedRerankPolicy

CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID = (
    "bijux.canon.index.hybrid-retrieval.content-evidence-v2"
)
CONTENT_EVIDENCE_RETRIEVAL_POLICY_V1_ID = (
    "bijux.canon.index.hybrid-retrieval.content-evidence-v1"
)
LEGACY_RETRIEVAL_POLICY_ID = "bijux.canon.index.hybrid-retrieval.legacy-v1"


@dataclass(frozen=True, slots=True)
class HybridRetrievalPolicy:
    """Candidate, fusion, fallback, and final-output bounds for hybrid retrieval."""

    policy_id: str
    candidate_multiplier: int
    maximum_candidate_limit: int
    admit_full_lexical_pool: bool
    rank_constant: int
    lexical_weight: float
    dense_weight: float
    fallback_to_exact_on_ann_refusal: bool
    maximum_dense_attempts: int
    vex_max_memory_bytes: int
    vex_max_ef_search: int
    vex_minimum_recall: float
    vex_require_witness: bool

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("hybrid retrieval policy identity must not be empty")
        if not 1 <= self.candidate_multiplier <= 100:
            raise ValueError("hybrid candidate multiplier must be within 1..100")
        if not 10 <= self.maximum_candidate_limit <= 1000:
            raise ValueError("hybrid maximum candidate limit must be within 10..1000")
        if not 1 <= self.rank_constant <= 10_000:
            raise ValueError("hybrid RRF rank constant must be within 1..10000")
        if any(
            not math.isfinite(value) or value <= 0
            for value in (self.lexical_weight, self.dense_weight)
        ):
            raise ValueError("hybrid channel weights must be finite and positive")
        if not 1 <= self.maximum_dense_attempts <= 2:
            raise ValueError("hybrid dense attempts must be within 1..2")
        if min(self.vex_max_memory_bytes, self.vex_max_ef_search) <= 0:
            raise ValueError("hybrid VEX effort bounds must be positive")
        if not 0.0 <= self.vex_minimum_recall <= 1.0:
            raise ValueError("hybrid VEX minimum recall must be within [0,1]")
        if self.fallback_to_exact_on_ann_refusal and self.maximum_dense_attempts != 2:
            raise ValueError("hybrid exact fallback requires two bounded attempts")

    @property
    def identity_sha256(self) -> str:
        """Bind every behavior-affecting parameter to one immutable identity."""

        raw = json.dumps(
            self.behavior_record(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @property
    def uses_evidence_planning(self) -> bool:
        """Return whether this version executes bounded content evidence needs."""

        return self.policy_id == CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID

    def behavior_record(self) -> dict[str, object]:
        """Return the complete symbolic policy without request-specific bounds."""

        record: dict[str, object] = asdict(self)
        if self.uses_evidence_planning:
            record["evidence_planning"] = {
                "max_subqueries": 8,
                "per_query_top_k": "candidate_limit",
                "planning_policy_id": EVIDENCE_PLANNING_POLICY_ID,
                "top_k": "requested_top_k",
            }
            record["planned_rerank"] = asdict(PlannedRerankPolicy())
        return record

    def candidate_limit(self, top_k: int) -> int:
        """Resolve the bounded candidate pool for a caller output limit."""

        if not 1 <= top_k <= 1000:
            raise ValueError("hybrid output limit must be within 1..1000")
        return max(
            top_k,
            min(self.maximum_candidate_limit, top_k * self.candidate_multiplier),
        )

    def lexical_limit(self, top_k: int) -> int:
        """Resolve symmetric lexical admission when the policy requires it."""

        return self.candidate_limit(top_k) if self.admit_full_lexical_pool else top_k

    def fusion_policy(self, *, top_k: int) -> RrfFusionPolicy:
        """Return the deterministic RRF pool policy for one request."""

        return RrfFusionPolicy(
            rank_constant=self.rank_constant,
            lexical_weight=self.lexical_weight,
            dense_weight=self.dense_weight,
            top_k=self.candidate_limit(top_k),
        )

    def vex_budget(
        self,
        *,
        max_latency_ms: float,
        max_candidates: int,
    ) -> VexExecutionBudget:
        """Resolve the witnessed dense-execution budget for one bounded attempt."""

        return VexExecutionBudget(
            max_latency_ms=max_latency_ms,
            max_memory_bytes=self.vex_max_memory_bytes,
            max_candidates=max_candidates,
            max_ef_search=self.vex_max_ef_search,
            minimum_recall=self.vex_minimum_recall,
            require_witness=self.vex_require_witness,
        )

    def record(self, *, top_k: int) -> dict[str, object]:
        """Return public, secret-free effective policy evidence."""

        return {
            **self.behavior_record(),
            "candidate_limit": self.candidate_limit(top_k),
            "identity_sha256": self.identity_sha256,
            "lexical_limit": self.lexical_limit(top_k),
            "requested_top_k": top_k,
            "schema_version": "bijux.canon.index.hybrid-retrieval-policy.v1",
        }


_POLICIES = {
    CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID: HybridRetrievalPolicy(
        policy_id=CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID,
        candidate_multiplier=50,
        maximum_candidate_limit=500,
        admit_full_lexical_pool=True,
        rank_constant=1,
        lexical_weight=1.0,
        dense_weight=2.0,
        fallback_to_exact_on_ann_refusal=True,
        maximum_dense_attempts=2,
        vex_max_memory_bytes=512 * 1024 * 1024,
        vex_max_ef_search=10_000,
        vex_minimum_recall=0.9,
        vex_require_witness=True,
    ),
    CONTENT_EVIDENCE_RETRIEVAL_POLICY_V1_ID: HybridRetrievalPolicy(
        policy_id=CONTENT_EVIDENCE_RETRIEVAL_POLICY_V1_ID,
        candidate_multiplier=50,
        maximum_candidate_limit=500,
        admit_full_lexical_pool=True,
        rank_constant=1,
        lexical_weight=1.0,
        dense_weight=2.0,
        fallback_to_exact_on_ann_refusal=True,
        maximum_dense_attempts=2,
        vex_max_memory_bytes=512 * 1024 * 1024,
        vex_max_ef_search=10_000,
        vex_minimum_recall=0.9,
        vex_require_witness=True,
    ),
    LEGACY_RETRIEVAL_POLICY_ID: HybridRetrievalPolicy(
        policy_id=LEGACY_RETRIEVAL_POLICY_ID,
        candidate_multiplier=4,
        maximum_candidate_limit=1000,
        admit_full_lexical_pool=False,
        rank_constant=60,
        lexical_weight=1.0,
        dense_weight=1.0,
        fallback_to_exact_on_ann_refusal=False,
        maximum_dense_attempts=1,
        vex_max_memory_bytes=512 * 1024 * 1024,
        vex_max_ef_search=10_000,
        vex_minimum_recall=0.9,
        vex_require_witness=True,
    ),
}


def resolve_hybrid_retrieval_policy(policy_id: str) -> HybridRetrievalPolicy:
    """Resolve one known policy or reject silent parameter drift."""

    try:
        return _POLICIES[policy_id]
    except KeyError as error:
        raise ValueError(f"unsupported hybrid retrieval policy: {policy_id}") from error


__all__ = [
    "CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID",
    "CONTENT_EVIDENCE_RETRIEVAL_POLICY_V1_ID",
    "HybridRetrievalPolicy",
    "LEGACY_RETRIEVAL_POLICY_ID",
    "resolve_hybrid_retrieval_policy",
]
