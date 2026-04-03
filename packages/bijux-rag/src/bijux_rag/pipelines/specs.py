# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 9: serializable pipeline specs (end-of-Bijux RAG).

Specs are pure data. They can be serialized, transported, and reconstructed
deterministically using allow-listed registries.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias, TypeVar, cast

from bijux_rag.result.types import Err, ErrInfo, Ok, Result, is_err, is_ok

T = TypeVar("T")
U = TypeVar("U")

ErrorPolicy: TypeAlias = Literal["collect", "drop", "fail_fast"]


@dataclass(frozen=True, slots=True)
class OperatorSpec:
    type: Literal["Map", "FlatMap"]
    func_id: str
    error_policy: ErrorPolicy = "collect"


@dataclass(frozen=True, slots=True)
class PipelineSpec:
    ops: tuple[OperatorSpec, ...]

    def __post_init__(self) -> None:
        if not self.ops:
            raise ValueError("PipelineSpec.ops must be non-empty")


Func: TypeAlias = Callable[[Any], Any]
SpecRegistry: TypeAlias = Mapping[str, Func]


def canonical_json(obj: object) -> str:
    """Canonical JSON for hashing (sorted keys, no whitespace)."""

    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def spec_hash(spec: PipelineSpec) -> str:
    payload = {
        "ops": [
            {"type": op.type, "func_id": op.func_id, "error_policy": op.error_policy}
            for op in spec.ops
        ]
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _apply_policy(
    it: Iterator[Result[T, ErrInfo]],
    policy: ErrorPolicy,
) -> Iterator[Result[T, ErrInfo]]:
    if policy == "collect":
        return it
    if policy == "drop":
        return (r for r in it if is_ok(r))
    if policy == "fail_fast":

        def _ff() -> Iterator[Result[T, ErrInfo]]:
            for r in it:
                if is_err(r):
                    raise RuntimeError(r.error.msg)
                yield r

        return _ff()
    raise ValueError(f"unknown ErrorPolicy: {policy}")


def reconstruct_pipeline(
    spec: PipelineSpec,
    registry: SpecRegistry,
    *,
    allow_list: set[str] | None = None,
) -> Result[Callable[[Iterable[Result[Any, ErrInfo]]], Iterator[Result[Any, ErrInfo]]], ErrInfo]:
    allow = allow_list if allow_list is not None else set(registry.keys())

    funcs: list[tuple[Literal["Map", "FlatMap"], str, Callable[[Any], Any], ErrorPolicy]] = []
    for op in spec.ops:
        if op.func_id not in allow:
            return Err(ErrInfo(code="DISALLOWED", msg=f"func_id not allowed: {op.func_id}"))
        f = registry.get(op.func_id)
        if f is None:
            return Err(ErrInfo(code="UNKNOWN_FUNC", msg=f"unknown func_id: {op.func_id}"))
        funcs.append((op.type, op.func_id, f, op.error_policy))

    def run(stream: Iterable[Result[Any, ErrInfo]]) -> Iterator[Result[Any, ErrInfo]]:
        it: Iterator[Any] = iter(stream)
        for typ, fid, f, pol in funcs:
            if typ == "Map":

                def _map_one(
                    r: Result[Any, ErrInfo],
                    *,
                    _fid: str = fid,
                    _f: Callable[[Any], Any] = f,
                ) -> Result[Any, ErrInfo]:
                    if isinstance(r, Err):
                        return r
                    try:
                        return Ok(_f(r.value))
                    except Exception as exc:
                        return Err(ErrInfo.from_exception(exc, stage=_fid))

                it = _apply_policy(
                    (_map_one(r) for r in cast(Iterator[Result[Any, ErrInfo]], it)),
                    pol,
                )
            elif typ == "FlatMap":

                def _flat(
                    r: Result[Any, ErrInfo],
                    *,
                    _fid: str = fid,
                    _f: Callable[[Any], Any] = f,
                ) -> Iterator[Result[Any, ErrInfo]]:
                    if isinstance(r, Err):
                        yield r
                        return
                    try:
                        for x in cast(Iterable[Any], _f(r.value)):
                            yield Ok(x)
                    except Exception as exc:
                        yield Err(ErrInfo.from_exception(exc, stage=_fid))

                it = _apply_policy(
                    (y for r in cast(Iterator[Result[Any, ErrInfo]], it) for y in _flat(r)),
                    pol,
                )
            else:
                raise ValueError(f"unsupported op type {typ}")
        return cast(Iterator[Result[Any, ErrInfo]], it)

    return Ok(run)


__all__ = [
    "ErrorPolicy",
    "OperatorSpec",
    "PipelineSpec",
    "SpecRegistry",
    "canonical_json",
    "spec_hash",
    "reconstruct_pipeline",
]
