# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.boundaries.adapters.serde import (
    MIGRATORS,
    Envelope,
    dec_option,
    dec_result,
    enc_option,
    enc_result,
    from_json,
    from_msgpack,
    migrate,
    to_json,
    to_msgpack,
)
from bijux_rag.fp.core import Err, ErrInfo, NoneVal, Ok, Some


@given(opt=st.one_of(st.builds(Some, st.integers()), st.just(NoneVal())))
def test_option_json_roundtrip(opt) -> None:
    enc = enc_option()
    dec = dec_option()
    s = to_json(opt, enc)
    back = from_json(s, dec)
    assert back == opt


_msgpack_int = st.integers(min_value=-(2**63), max_value=2**64 - 1)
_errinfo_safe = st.builds(
    ErrInfo,
    code=st.text(),
    msg=st.text(),
    stage=st.just(""),
    path=st.just(()),
    cause=st.none(),
    ctx=st.none(),
)


@given(res=st.one_of(st.builds(Ok, _msgpack_int), st.builds(Err, _errinfo_safe)))
def test_result_msgpack_roundtrip(res) -> None:
    enc = enc_result()
    dec = dec_result()
    b = to_msgpack(res, enc)
    back = from_msgpack(b, dec)
    assert back == res


def test_chunk_v1_migration() -> None:
    def migrate_chunk_v1_to_v2(env: Envelope) -> Envelope:
        if env.tag != "chunk" or env.ver != 1:
            return env
        payload = dict(env.payload)
        payload.setdefault("metadata", {})
        return Envelope(tag="chunk", ver=2, payload=payload)

    old = dict(MIGRATORS)
    try:
        MIGRATORS.clear()
        MIGRATORS[("chunk", 1)] = migrate_chunk_v1_to_v2
        v1_payload = {"text": "hello", "embedding": [0.1, 0.2]}
        env_v1 = Envelope(tag="chunk", ver=1, payload=v1_payload)
        env_v2 = migrate(env_v1)
        assert env_v2.ver == 2
        assert env_v2.payload["metadata"] == {}
    finally:
        MIGRATORS.clear()
        MIGRATORS.update(old)
