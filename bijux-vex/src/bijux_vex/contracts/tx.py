# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Transaction contract.

All mutations must occur within a Tx. A Tx must either commit atomically or abort
without side effects. Backends must provide deterministic behavior.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType


class Tx(ABC):
    """Transactional context wrapping a set of operations."""

    @property
    @abstractmethod
    def tx_id(self) -> str:
        """Stable identifier for the transaction."""

    @abstractmethod
    def commit(self) -> None:
        """Finalize the transaction; must be atomic."""

    @abstractmethod
    def abort(self) -> None:
        """Abort and roll back any staged mutations."""

    def __enter__(self) -> Tx:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        if exc:
            self.abort()
            return False
        if getattr(self, "_active", True):
            self.commit()
            return True
        return False
