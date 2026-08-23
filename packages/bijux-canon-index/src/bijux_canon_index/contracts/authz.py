# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""
Authorization contracts for mutations and scoped retrieval.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from typing import Any

from bijux_canon_index.contracts.tx import Tx
from bijux_canon_index.core.errors import AuthzDeniedError
from bijux_canon_index.domain.metadata_filters import MetadataFilter


def _normalized_scope_values(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    if any(not isinstance(value, str) or not value for value in values):
        raise ValueError(f"retrieval authorization {name} must be non-empty strings")
    return tuple(sorted(set(values)))


@dataclass(frozen=True, slots=True)
class RetrievalAuthorizationScope:
    """Immutable generation and source authority for one retrieval operation."""

    generation_ids: tuple[str, ...]
    source_ids: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    actor: str | None = None
    schema_version: str = "bijux.canon.index.retrieval_authorization_scope.v1"

    def __post_init__(self) -> None:
        if self.schema_version != (
            "bijux.canon.index.retrieval_authorization_scope.v1"
        ):
            raise ValueError("retrieval authorization scope schema is unsupported")
        object.__setattr__(
            self,
            "generation_ids",
            _normalized_scope_values("generation_ids", self.generation_ids),
        )
        object.__setattr__(
            self,
            "source_ids",
            _normalized_scope_values("source_ids", self.source_ids),
        )
        object.__setattr__(
            self,
            "paths",
            _normalized_scope_values("paths", self.paths),
        )
        if not self.generation_ids:
            raise ValueError("retrieval authorization requires a generation scope")
        if not self.source_ids and not self.paths:
            raise ValueError("retrieval authorization requires a source or path scope")
        if self.actor is not None and not self.actor.strip():
            raise ValueError("retrieval authorization actor must be null or non-empty")

    @property
    def artifact_id(self) -> str:
        """Return the complete content identity of the declared authority."""

        encoded = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def authorize_retrieval_filter(
    scope: RetrievalAuthorizationScope | None,
    *,
    generation_id: str,
    requested: MetadataFilter | None,
) -> MetadataFilter | None:
    """Return a scope-constrained filter or reject requested authority widening."""

    if scope is None:
        return requested
    if generation_id not in scope.generation_ids:
        raise AuthzDeniedError(message="retrieval generation is outside authority")
    selected = requested or MetadataFilter()
    effective: dict[str, tuple[str, ...]] = {}
    match_none = selected.match_none
    for name, allowed in (("source_ids", scope.source_ids), ("paths", scope.paths)):
        requested_values = getattr(selected, name)
        if not allowed:
            effective[name] = requested_values
        elif not requested_values:
            effective[name] = allowed
        else:
            intersection = tuple(sorted(set(requested_values).intersection(allowed)))
            effective[name] = intersection
            match_none = match_none or not intersection
    return replace(
        selected,
        match_none=match_none,
        source_ids=effective["source_ids"],
        paths=effective["paths"],
    )


class Authz(ABC):
    """Authorization interface invoked before any mutation."""

    @abstractmethod
    def check(
        self,
        tx: Tx,
        *,
        action: str,
        resource: str,
        actor: str | None = None,
        context: Any | None = None,
    ) -> None:
        """
        Raise if the actor is not authorized for the action.
        Must be deterministic for identical inputs.
        """


class AllowAllAuthz(Authz):
    """Default permissive authorization used in tests."""

    def check(
        self,
        tx: Tx,
        *,
        action: str,
        resource: str,
        actor: str | None = None,
        context: Any | None = None,
    ) -> None:
        """Handle check."""
        return


class DenyAllAuthz(Authz):
    """Strict authorization that denies any mutation but allows reads."""

    def check(
        self,
        tx: Tx,
        *,
        action: str,
        resource: str,
        actor: str | None = None,
        context: Any | None = None,
    ) -> None:
        """Handle check."""
        readish = action.startswith(("get", "list", "query", "read"))
        if not readish:
            raise AuthzDeniedError(
                message=f"Action '{action}' on '{resource}' denied by policy"
            )
        return


__all__ = [
    "AllowAllAuthz",
    "Authz",
    "DenyAllAuthz",
    "RetrievalAuthorizationScope",
    "authorize_retrieval_filter",
]
