# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Authorization hooks for all mutations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from bijux_vex.contracts.tx import Tx


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
        return None


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
        readish = action.startswith(("get", "list", "query", "read"))
        if not readish:
            from bijux_vex.core.errors import AuthzDeniedError

            raise AuthzDeniedError(
                message=f"Action '{action}' on '{resource}' denied by policy"
            )
        return None
