# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from dataclasses import dataclass

from bijux_rag.domain.effects.io_plan import io_delay, io_pure, perform
from bijux_rag.domain.effects.tx import Session, Tx, TxProtocol, with_tx
from bijux_rag.result.types import Err, ErrInfo, Ok, Result


@dataclass
class FakeTxCap(TxProtocol):
    begin_calls: int = 0
    commit_calls: int = 0
    rollback_calls: int = 0
    commit_fails: bool = False
    rollback_fails: bool = False

    def begin(self, session: Session):
        def act() -> Result[Result[Tx, ErrInfo], ErrInfo]:
            self.begin_calls += 1
            return Ok(Ok(Tx(session=session, tx_id="t1")))

        return io_delay(act)

    def commit(self, tx: Tx):
        def act() -> Result[Result[None, ErrInfo], ErrInfo]:
            self.commit_calls += 1
            if self.commit_fails:
                return Ok(Err(ErrInfo(code="COMMIT_FAIL", msg=tx.tx_id)))
            return Ok(Ok(None))

        return io_delay(act)

    def rollback(self, tx: Tx):
        def act() -> Result[Result[None, ErrInfo], ErrInfo]:
            self.rollback_calls += 1
            if self.rollback_fails:
                return Ok(Err(ErrInfo(code="ROLLBACK_FAIL", msg=tx.tx_id)))
            return Ok(Ok(None))

        return io_delay(act)


def test_with_tx_commits_on_success() -> None:
    tx_cap = FakeTxCap()
    session = Session(conn_id="c1")

    def body(_: Tx):
        return io_pure(Ok(123))

    assert perform(with_tx(tx_cap, session, body)) == Ok(Ok(123))
    assert (tx_cap.begin_calls, tx_cap.commit_calls, tx_cap.rollback_calls) == (1, 1, 0)


def test_with_tx_rolls_back_on_failure() -> None:
    tx_cap = FakeTxCap()
    session = Session(conn_id="c1")

    def body(_: Tx):
        return io_pure(Err(ErrInfo(code="BODY_FAIL", msg="boom")))

    assert perform(with_tx(tx_cap, session, body)) == Ok(Err(ErrInfo(code="BODY_FAIL", msg="boom")))
    assert (tx_cap.begin_calls, tx_cap.commit_calls, tx_cap.rollback_calls) == (1, 0, 1)


def test_with_tx_commit_failure_dominates() -> None:
    tx_cap = FakeTxCap(commit_fails=True)
    session = Session(conn_id="c1")

    def body(_: Tx):
        return io_pure(Ok("done"))

    assert perform(with_tx(tx_cap, session, body)) == Ok(Err(ErrInfo(code="COMMIT_FAIL", msg="t1")))
    assert (tx_cap.begin_calls, tx_cap.commit_calls, tx_cap.rollback_calls) == (1, 1, 0)


def test_with_tx_rollback_best_effort_preserves_body_err() -> None:
    tx_cap = FakeTxCap(rollback_fails=True)
    session = Session(conn_id="c1")

    def body(_: Tx):
        return io_pure(Err(ErrInfo(code="BODY_FAIL", msg="boom")))

    assert perform(with_tx(tx_cap, session, body)) == Ok(Err(ErrInfo(code="BODY_FAIL", msg="boom")))
    assert (tx_cap.begin_calls, tx_cap.commit_calls, tx_cap.rollback_calls) == (1, 0, 1)
