# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Composition root for installed canonical package application services."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bijux_canon_agent.application.execution_service import run_offline_agent
from bijux_canon_index.application import (
    DenseCandidateService,
    IndexService,
    LexicalCandidateService,
    RetrievalOutcomeService,
)
from bijux_canon_index.core.contracts.execution_abi import (
    assert_execution_abi,
    execution_abi_payload,
)
from bijux_canon_index.infra.embeddings.local_model import LocalEmbeddingModel
from bijux_canon_ingest.application.canonical_ingest import CanonicalIngestRuntime
from bijux_canon_ingest.application.corpus_snapshot import build_corpus_snapshot
from bijux_canon_ingest.domain.corpus_snapshot import CorpusSnapshot
from bijux_canon_reason.application.run_workflow import run_app
from bijux_canon_reason.core.system_contract import assert_system_contract

from bijux_canon_runtime.core.package_versions import distribution_version
from bijux_canon_runtime.model.execution.request_plan import DagOperation
from bijux_canon_runtime.runtime.execution.canonical_adapters import (
    CanonicalAgentAdapterV1,
    CanonicalReasonAdapterV1,
)


@dataclass(frozen=True, slots=True)
class InstalledServiceCapability:
    """Verified installed implementation bound to typed Runtime operations."""

    protocol_version: str
    owner_distribution: str
    distribution_version: str
    implementation_module: str
    implementation_name: str
    operations: tuple[DagOperation, ...]
    capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.protocol_version != "1.0":
            raise ValueError("installed service protocol version is unsupported")
        if not self.distribution_version or self.distribution_version == "0.0.0":
            raise RuntimeError(
                f"required distribution is not installed: {self.owner_distribution}"
            )
        expected_prefix = self.owner_distribution.replace("-", "_") + "."
        if not self.implementation_module.startswith(expected_prefix):
            raise ValueError("service implementation is not owned by its distribution")
        if not self.implementation_name.strip() or not self.operations:
            raise ValueError("service implementation and operations are required")
        if len(set(self.operations)) != len(self.operations):
            raise ValueError("service operations must be unique")
        if not self.capabilities or len(set(self.capabilities)) != len(
            self.capabilities
        ):
            raise ValueError("service capabilities must be nonempty and unique")


@dataclass(frozen=True, slots=True)
class CanonicalServiceComposition:
    """Concrete installed services owned by the Runtime composition root."""

    ingest: CanonicalIngestRuntime
    snapshot_builder: Callable[..., CorpusSnapshot]
    index: IndexService
    lexical_retrieval_type: type[LexicalCandidateService]
    dense_retrieval_type: type[DenseCandidateService]
    retrieval_outcome_type: type[RetrievalOutcomeService]
    embedding_type: type[LocalEmbeddingModel]
    reason: CanonicalReasonAdapterV1
    agent: CanonicalAgentAdapterV1
    capabilities: tuple[InstalledServiceCapability, ...]

    def require_operations(self, operations: tuple[DagOperation, ...]) -> None:
        """Reject a plan whose operation has no declared installed owner."""
        available = {
            operation
            for capability in self.capabilities
            for operation in capability.operations
        }
        missing = set(operations).difference(available)
        if missing:
            raise RuntimeError(
                "installed service composition lacks operations: "
                + ", ".join(sorted(item.value for item in missing))
            )

    def capability_manifest(self) -> tuple[dict[str, object], ...]:
        """Return deterministic provenance for the composed package services."""
        return tuple(
            {
                "capabilities": list(capability.capabilities),
                "distribution_version": capability.distribution_version,
                "implementation": (
                    f"{capability.implementation_module}."
                    f"{capability.implementation_name}"
                ),
                "operations": [item.value for item in capability.operations],
                "owner_distribution": capability.owner_distribution,
                "protocol_version": capability.protocol_version,
            }
            for capability in self.capabilities
        )


def compose_canonical_services(
    *,
    working_root: Path,
    index_registry_root: Path,
) -> CanonicalServiceComposition:
    """Bind exact installed application APIs and verify their declared contracts."""
    if not working_root.is_absolute() or not index_registry_root.is_absolute():
        raise ValueError("canonical service roots must be absolute paths")
    assert_execution_abi()
    assert_system_contract()
    index_abi = execution_abi_payload()
    abi_version = str(index_abi["abi_version"])
    versions = {
        name: distribution_version(name)
        for name in (
            "bijux-canon-agent",
            "bijux-canon-index",
            "bijux-canon-ingest",
            "bijux-canon-reason",
        )
    }
    capabilities = (
        InstalledServiceCapability(
            protocol_version="1.0",
            owner_distribution="bijux-canon-ingest",
            distribution_version=versions["bijux-canon-ingest"],
            implementation_module=(CanonicalIngestRuntime.__module__),
            implementation_name=CanonicalIngestRuntime.__name__,
            operations=(DagOperation.INGEST,),
            capabilities=(
                "recursive-source-discovery",
                "typed-source-admission",
                "exact-source-extraction",
            ),
        ),
        InstalledServiceCapability(
            protocol_version="1.0",
            owner_distribution="bijux-canon-ingest",
            distribution_version=versions["bijux-canon-ingest"],
            implementation_module=build_corpus_snapshot.__module__,
            implementation_name=build_corpus_snapshot.__name__,
            operations=(DagOperation.SNAPSHOT,),
            capabilities=(
                "canonical-corpus-snapshot",
                "stable-document-order",
                "content-addressed-membership",
            ),
        ),
        InstalledServiceCapability(
            protocol_version="1.0",
            owner_distribution="bijux-canon-index",
            distribution_version=versions["bijux-canon-index"],
            implementation_module=LocalEmbeddingModel.__module__,
            implementation_name=LocalEmbeddingModel.__name__,
            operations=(DagOperation.EMBED,),
            capabilities=(
                "locked-local-embedding",
                "offline-model-verification",
                "bounded-batch-inference",
            ),
        ),
        InstalledServiceCapability(
            protocol_version="1.0",
            owner_distribution="bijux-canon-index",
            distribution_version=versions["bijux-canon-index"],
            implementation_module=IndexService.__module__,
            implementation_name=IndexService.__name__,
            operations=(
                DagOperation.LEXICAL_INDEX,
                DagOperation.DENSE_INDEX,
            ),
            capabilities=(
                f"execution-abi:{abi_version}",
                "sqlite-fts5",
                "faiss-flat-ip",
                "faiss-hnsw",
            ),
        ),
        InstalledServiceCapability(
            protocol_version="1.0",
            owner_distribution="bijux-canon-index",
            distribution_version=versions["bijux-canon-index"],
            implementation_module=RetrievalOutcomeService.__module__,
            implementation_name=RetrievalOutcomeService.__name__,
            operations=(DagOperation.RETRIEVE,),
            capabilities=(
                "generation-bound-lexical",
                "required-channel-coordination",
                "typed-nonusable-outcomes",
            ),
        ),
        InstalledServiceCapability(
            protocol_version="1.0",
            owner_distribution="bijux-canon-index",
            distribution_version=versions["bijux-canon-index"],
            implementation_module=DenseCandidateService.__module__,
            implementation_name=DenseCandidateService.__name__,
            operations=(DagOperation.RETRIEVE,),
            capabilities=(
                "vex-dense-retrieval",
                "exact-search-witness",
                "persisted-execution-artifact",
            ),
        ),
        InstalledServiceCapability(
            protocol_version="1.0",
            owner_distribution="bijux-canon-reason",
            distribution_version=versions["bijux-canon-reason"],
            implementation_module=run_app.__module__,
            implementation_name=run_app.__name__,
            operations=(DagOperation.REASON,),
            capabilities=(
                "credential-free-runtime",
                "typed-claim-trace",
                "verification-report",
            ),
        ),
        InstalledServiceCapability(
            protocol_version="1.0",
            owner_distribution="bijux-canon-agent",
            distribution_version=versions["bijux-canon-agent"],
            implementation_module=run_offline_agent.__module__,
            implementation_name=run_offline_agent.__name__,
            operations=(DagOperation.AGENT,),
            capabilities=(
                "bounded-offline-execution",
                "causal-agent-trace",
                "cooperative-cancellation",
            ),
        ),
    )
    composition = CanonicalServiceComposition(
        ingest=CanonicalIngestRuntime(),
        snapshot_builder=build_corpus_snapshot,
        index=IndexService(index_registry_root),
        lexical_retrieval_type=LexicalCandidateService,
        dense_retrieval_type=DenseCandidateService,
        retrieval_outcome_type=RetrievalOutcomeService,
        embedding_type=LocalEmbeddingModel,
        reason=CanonicalReasonAdapterV1(),
        agent=CanonicalAgentAdapterV1(working_root=working_root),
        capabilities=capabilities,
    )
    composition.require_operations(
        (
            DagOperation.INGEST,
            DagOperation.SNAPSHOT,
            DagOperation.EMBED,
            DagOperation.LEXICAL_INDEX,
            DagOperation.DENSE_INDEX,
            DagOperation.RETRIEVE,
            DagOperation.REASON,
            DagOperation.AGENT,
        )
    )
    if not callable(run_offline_agent) or not callable(run_app):
        raise RuntimeError("canonical agent and reason services are not callable")
    return composition


__all__ = [
    "CanonicalServiceComposition",
    "InstalledServiceCapability",
    "compose_canonical_services",
]
