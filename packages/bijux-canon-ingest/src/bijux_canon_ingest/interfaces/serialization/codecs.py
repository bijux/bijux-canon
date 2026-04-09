# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Serialization codecs for Option, Result, and Validation values."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import (
    Any,
    TypeVar,
    cast,
)

from bijux_canon_ingest.fp.core import (
    Err,
    ErrInfo,
    NoneVal,
    Ok,
    Option,
    Result,
    Some,
    Validation,
    VFailure,
    VSuccess,
)
from bijux_canon_ingest.interfaces.serialization.envelopes import (
    MIGRATORS,
    Decoder,
    Encoder,
    Envelope,
    from_json,
    from_msgpack,
    iter_msgpack,
    iter_ndjson,
    migrate,
    to_json,
    to_msgpack,
)

T = TypeVar("T")
JSON = str | int | float | bool | None | list["JSON"] | dict[str, "JSON"]


def json_encoder(x: Any) -> JSON:
    return cast(JSON, x)


def json_decoder(j: JSON) -> Any:
    return j


def _default_enc_err(e: ErrInfo) -> JSON:
    out: dict[str, JSON] = {"code": e.code, "msg": e.msg}
    if e.stage:
        out["stage"] = e.stage
    if e.path:
        out["path"] = [int(i) for i in e.path]
    return out


def _default_dec_err(j: JSON) -> ErrInfo:
    if not isinstance(j, Mapping):
        raise ValueError("ErrInfo payload must be an object")
    code = j.get("code")
    msg = j.get("msg")
    if not isinstance(code, str) or not isinstance(msg, str):
        raise ValueError("ErrInfo requires string fields: code, msg")
    stage = j.get("stage", "")
    if not isinstance(stage, str):
        raise ValueError("ErrInfo.stage must be str when present")
    path_val = j.get("path", [])
    if not isinstance(path_val, list):
        raise ValueError("ErrInfo.path must be list[int] when present")
    path_items: list[int] = []
    for x in path_val:
        if not isinstance(x, int):
            raise ValueError("ErrInfo.path must be list[int] when present")
        path_items.append(x)
    return ErrInfo(code=code, msg=msg, stage=stage, path=tuple(path_items))


def enc_option(enc_val: Callable[[T], JSON] | None = None) -> Encoder[Option[T]]:
    ev = enc_val or cast(Callable[[T], JSON], json_encoder)

    def _enc(x: Option[T]) -> Envelope:
        match x:
            case Some(value=v):
                return Envelope(
                    tag="option", ver=1, payload={"kind": "some", "value": ev(v)}
                )
            case NoneVal():
                return Envelope(tag="option", ver=1, payload={"kind": "none"})
            case other:
                raise TypeError(f"Unexpected Option variant: {other!r}")

    return _enc


def dec_option(dec_val: Callable[[JSON], T] | None = None) -> Decoder[Option[T]]:
    dv = dec_val or cast(Callable[[JSON], T], json_decoder)

    def _dec(env: Envelope) -> Option[T]:
        if env.tag != "option":
            raise ValueError(f"expected tag 'option', got {env.tag}")
        if env.ver != 1:
            raise ValueError(f"unknown version {env.ver}")
        kind = env.payload.get("kind")
        if kind == "some":
            return Some(dv(env.payload["value"]))
        if kind == "none":
            return NoneVal()
        raise ValueError(f"invalid kind {kind!r}")

    return _dec


def enc_result(
    enc_val: Callable[[T], JSON] | None = None,
    enc_err: Callable[[ErrInfo], JSON] | None = None,
) -> Encoder[Result[T, ErrInfo]]:
    ev = enc_val or cast(Callable[[T], JSON], json_encoder)
    ee = enc_err or _default_enc_err

    def _enc(x: Result[T, ErrInfo]) -> Envelope:
        match x:
            case Ok(value=v):
                return Envelope(
                    tag="result", ver=1, payload={"kind": "ok", "value": ev(v)}
                )
            case Err(error=e):
                return Envelope(
                    tag="result", ver=1, payload={"kind": "err", "error": ee(e)}
                )
            case other:
                raise TypeError(f"Unexpected Result variant: {other!r}")

    return _enc


def dec_result(
    dec_val: Callable[[JSON], T] | None = None,
    dec_err: Callable[[JSON], ErrInfo] | None = None,
) -> Decoder[Result[T, ErrInfo]]:
    dv = dec_val or cast(Callable[[JSON], T], json_decoder)
    de = dec_err or _default_dec_err

    def _dec(env: Envelope) -> Result[T, ErrInfo]:
        if env.tag != "result":
            raise ValueError(f"expected tag 'result', got {env.tag}")
        if env.ver != 1:
            raise ValueError(f"unknown version {env.ver}")
        kind = env.payload.get("kind")
        if kind == "ok":
            return Ok(dv(env.payload["value"]))
        if kind == "err":
            return Err(de(env.payload["error"]))
        raise ValueError(f"invalid kind {kind!r}")

    return _dec


def enc_validation(
    enc_val: Callable[[T], JSON] | None = None,
    enc_err: Callable[[ErrInfo], JSON] | None = None,
) -> Encoder[Validation[T, ErrInfo]]:
    ev = enc_val or cast(Callable[[T], JSON], json_encoder)
    ee = enc_err or _default_enc_err

    def _enc(x: Validation[T, ErrInfo]) -> Envelope:
        match x:
            case VSuccess(value=v):
                return Envelope(
                    tag="validation",
                    ver=1,
                    payload={"kind": "v_success", "value": ev(v)},
                )
            case VFailure(errors=es):
                return Envelope(
                    tag="validation",
                    ver=1,
                    payload={"kind": "v_failure", "errors": [ee(e) for e in es]},
                )
            case other:
                raise TypeError(f"Unexpected Validation variant: {other!r}")

    return _enc


def dec_validation(
    dec_val: Callable[[JSON], T] | None = None,
    dec_err: Callable[[JSON], ErrInfo] | None = None,
) -> Decoder[Validation[T, ErrInfo]]:
    dv = dec_val or cast(Callable[[JSON], T], json_decoder)
    de = dec_err or _default_dec_err

    def _dec(env: Envelope) -> Validation[T, ErrInfo]:
        if env.tag != "validation":
            raise ValueError(f"expected tag 'validation', got {env.tag}")
        if env.ver != 1:
            raise ValueError(f"unknown version {env.ver}")
        kind = env.payload.get("kind")
        if kind == "v_success":
            return VSuccess(dv(env.payload["value"]))
        if kind == "v_failure":
            errors_raw = env.payload.get("errors")
            if not isinstance(errors_raw, list):
                raise ValueError("validation.errors must be a JSON array")
            errs = [de(e) for e in errors_raw]
            if not errs:
                raise ValueError("VFailure requires non-empty errors")
            return VFailure(tuple(errs))
        raise ValueError(f"invalid kind {kind!r}")

    return _dec


@dataclass(frozen=True, slots=True)
class DecodeErr:
    path: tuple[str, ...] = ()
    msg: str = ""


def from_json_safe(s: str, dec: Decoder[T]) -> Validation[T, DecodeErr]:
    try:
        return VSuccess(from_json(s, dec))
    except Exception as exc:
        return VFailure((DecodeErr(msg=str(exc)),))


__all__ = [
    "Envelope",
    "Encoder",
    "Decoder",
    "enc_option",
    "dec_option",
    "enc_result",
    "dec_result",
    "enc_validation",
    "dec_validation",
    "to_json",
    "from_json",
    "to_msgpack",
    "from_msgpack",
    "from_json_safe",
    "MIGRATORS",
    "migrate",
    "iter_ndjson",
    "iter_msgpack",
]
