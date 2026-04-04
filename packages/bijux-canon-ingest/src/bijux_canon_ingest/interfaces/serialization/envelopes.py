# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Envelope transport and migration helpers for serialization codecs."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
import json
from typing import TYPE_CHECKING, Any, BinaryIO, TypeVar, cast

import msgpack

T = TypeVar("T")

JSON = str | int | float | bool | None | list["JSON"] | dict[str, "JSON"]

if TYPE_CHECKING:
    PackbFn = Callable[[Any], bytes]
    UnpackbFn = Callable[[bytes], Any]
else:
    PackbFn = Callable[[Any], bytes]
    UnpackbFn = Callable[[bytes], Any]

_packb: PackbFn = cast(PackbFn, msgpack.packb)
_unpackb: UnpackbFn = cast(UnpackbFn, msgpack.unpackb)

_MP_PACK: dict[str, object] = {"use_bin_type": True}
_MP_UNPACK: dict[str, object] = {"raw": False}


@dataclass(frozen=True, slots=True)
class Envelope:
    tag: str
    ver: int
    payload: dict[str, JSON]


Encoder = Callable[[T], Envelope]
Decoder = Callable[[Envelope], T]


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
    "Decoder",
    "Encoder",
    "Envelope",
    "MIGRATORS",
    "from_json",
    "from_msgpack",
    "iter_msgpack",
    "iter_ndjson",
    "migrate",
    "to_json",
    "to_msgpack",
]
