# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG serialization contracts: Envelope + JSON/MessagePack + migrations (end-of-Bijux RAG; adapters).

# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    Tuple,
    TypeAlias,
    TypeVar,
    cast,
)

import msgpack

from bijux_rag.fp.core import (
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

T = TypeVar("T")

JSON = str | int | float | bool | None | list["JSON"] | dict[str, "JSON"]

if TYPE_CHECKING:
    PackbFn = Callable[[Any], bytes]
    UnpackbFn = Callable[[bytes], Any]
    MsgpackUnpacker = msgpack.Unpacker
else:
    PackbFn = Callable[[Any], bytes]
    UnpackbFn = Callable[[bytes], Any]
    MsgpackUnpacker = Any

_packb: PackbFn = cast(PackbFn, msgpack.packb)
_unpackb: UnpackbFn = cast(UnpackbFn, msgpack.unpackb)


@dataclass(frozen=True, slots=True)
class Envelope:
    tag: str
    ver: int
    payload: dict[str, JSON]


Encoder: TypeAlias = Callable[[T], Envelope]
Decoder: TypeAlias = Callable[[Envelope], T]


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
                return Envelope(tag="option", ver=1, payload={"kind": "some", "value": ev(v)})
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
                return Envelope(tag="result", ver=1, payload={"kind": "ok", "value": ev(v)})
            case Err(error=e):
                return Envelope(tag="result", ver=1, payload={"kind": "err", "error": ee(e)})
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
                    tag="validation", ver=1, payload={"kind": "v_success", "value": ev(v)}
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


_MP_PACK: dict[str, object] = {"use_bin_type": True}
_MP_UNPACK: dict[str, object] = {"raw": False}


def _check_env(obj: Any) -> None:
    if not isinstance(obj, dict):
        raise ValueError("invalid envelope: not a dict")
    required = {"tag", "ver", "payload"}
    missing = required - set(obj)
    if missing:
        raise ValueError(f"invalid envelope: missing {missing}")
    if not isinstance(obj["tag"], str):
        raise ValueError("tag must be str")
    if not isinstance(obj["ver"], int):
        raise ValueError("ver must be int")
    if not isinstance(obj["payload"], dict):
        raise ValueError("payload must be dict")


def to_json(x: T, enc: Encoder[T]) -> str:
    env = enc(x)
    return json.dumps(
        {"tag": env.tag, "ver": env.ver, "payload": env.payload},
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def from_json(s: str, dec: Decoder[T]) -> T:
    obj = json.loads(s)
    _check_env(obj)
    env = Envelope(tag=obj["tag"], ver=obj["ver"], payload=obj["payload"])
    return dec(migrate(env))


def to_msgpack(x: T, enc: Encoder[T]) -> bytes:
    env = enc(x)
    return _packb({"tag": env.tag, "ver": env.ver, "payload": env.payload}, **_MP_PACK)


def from_msgpack(b: bytes, dec: Decoder[T]) -> T:
    obj = _unpackb(b, **_MP_UNPACK)
    _check_env(obj)
    env = Envelope(tag=obj["tag"], ver=obj["ver"], payload=obj["payload"])
    return dec(migrate(env))


@dataclass(frozen=True, slots=True)
class DecodeErr:
    path: Tuple[str, ...] = ()
    msg: str = ""


def from_json_safe(s: str, dec: Decoder[T]) -> Validation[T, DecodeErr]:
    try:
        return VSuccess(from_json(s, dec))
    except Exception as exc:
        return VFailure((DecodeErr(msg=str(exc)),))


MIGRATORS: dict[tuple[str, int], Callable[[Envelope], Envelope]] = {}
MAX_MIGRATION_STEPS = 32


def migrate(env: Envelope) -> Envelope:
    key = (env.tag, env.ver)
    steps = 0
    seen: set[tuple[str, int]] = set()
    while key in MIGRATORS:
        if key in seen:
            raise RuntimeError(f"migration cycle detected at {key}")
        seen.add(key)
        steps += 1
        if steps > MAX_MIGRATION_STEPS:
            raise RuntimeError("migration step limit exceeded")
        env = MIGRATORS[key](env)
        key = (env.tag, env.ver)
    return env


def iter_ndjson(fp: Iterable[str], dec: Decoder[T]) -> Iterator[T]:
    for line in fp:
        line = line.strip()
        if line:
            yield from_json(line, dec)


def iter_msgpack(fp: BinaryIO, dec: Decoder[T]) -> Iterator[T]:
    unpacker = msgpack.Unpacker(fp, **_MP_UNPACK)
    for obj in unpacker:
        _check_env(obj)
        yield dec(migrate(Envelope(obj["tag"], obj["ver"], obj["payload"])))


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
