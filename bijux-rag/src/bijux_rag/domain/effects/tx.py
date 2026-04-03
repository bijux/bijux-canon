# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: explicit Session/Tx data and transaction bracketing (domain)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Callable, Mapping, Protocol, TypeVar

from bijux_rag.result.types import Err, ErrInfo, Ok, Result

from .io_plan import IOPlan, io_bind, io_pure

T = TypeVar("T")


@dataclass(frozen=True)
class Session:
    """Long-lived connection state – immutable, explicit."""

    conn_id: str
    config: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))


def session_with(s: Session, **updates: str) -> Session:
    merged = dict(s.config)
    merged.update(updates)
    return replace(s, config=MappingProxyType(merged))


class TxProtocol(Protocol):
    """Begin/commit/rollback as explicit IOPlans.

    Implementers should make begin/commit/rollback idempotent where possible.
    """

    def begin(self, session: Session) -> IOPlan[Result["Tx", ErrInfo]]: ...

    def commit(self, tx: "Tx") -> IOPlan[Result[None, ErrInfo]]: ...

    def rollback(self, tx: "Tx") -> IOPlan[Result[None, ErrInfo]]: ...


@dataclass(frozen=True)
class Tx:
    session: Session
    tx_id: str


def with_tx(
    tx_cap: TxProtocol,
    session: Session,
    body: Callable[[Tx], IOPlan[Result[T, ErrInfo]]],
) -> IOPlan[Result[T, ErrInfo]]:
    """Bracket a body in begin/commit/rollback.

    Rollback is best-effort; commit failure dominates on success.
    """

    def after_begin(begin_res: Result[Tx, ErrInfo]) -> IOPlan[Result[T, ErrInfo]]:
        if isinstance(begin_res, Err):
            return io_pure(Err(begin_res.error))

        tx = begin_res.value

        def after_body(body_res: Result[T, ErrInfo]) -> IOPlan[Result[T, ErrInfo]]:
            if isinstance(body_res, Ok):
                return io_bind(
                    tx_cap.commit(tx),
                    lambda c_res: io_pure(body_res)
                    if isinstance(c_res, Ok)
                    else io_pure(Err(c_res.error)),
                )

            return io_bind(tx_cap.rollback(tx), lambda _: io_pure(body_res))

        return io_bind(body(tx), after_body)

    return io_bind(tx_cap.begin(session), after_begin)


__all__ = ["Session", "session_with", "TxProtocol", "Tx", "with_tx"]
