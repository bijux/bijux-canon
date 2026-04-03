# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Structured error reports from Result streams (end-of-Bijux RAG)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from types import MappingProxyType
from typing import Any, Generic, Iterable, Mapping, TypeVar

from bijux_rag.result import Err, ErrInfo, Ok, Result

from .breakers import BreakInfo

E = TypeVar("E")


@dataclass(frozen=True)
class ErrGroup(Generic[E]):
    count: int
    samples: tuple[E, ...]


@dataclass(frozen=True)
class ErrReport(Generic[E]):
    total_errs: int
    total_items: int
    by_code: Mapping[str, ErrGroup[E]]
    by_stage: Mapping[str, ErrGroup[E]]
    by_path_prefix: Mapping[tuple[int, ...], ErrGroup[E]]
    ctx_summary: Mapping[str, float]


def _normalize_err(e: Any) -> tuple[str, str, tuple[int, ...]]:
    code = getattr(e, "code", "UNKNOWN")
    stage = getattr(e, "stage", "UNKNOWN")
    path = getattr(e, "path", ())
    if isinstance(e, BreakInfo):
        code = e.code if str(e.code).startswith("BREAK/") else f"BREAK/{code}"
        stage = "BREAK"
    return str(code), str(stage), tuple(path)


@dataclass(slots=True)
class _GroupBuilder(Generic[E]):
    cap: int
    count: int = 0
    samples: list[E] = field(default_factory=list)

    def add(self, e: E) -> None:
        self.count += 1
        if len(self.samples) < self.cap:
            self.samples.append(e)

    def freeze(self) -> ErrGroup[E]:
        return ErrGroup(self.count, tuple(self.samples))


def fold_error_counts(stream: Iterable[Result[Any, E]]) -> Mapping[str, int]:
    counts: dict[str, int] = {}
    for r in stream:
        if isinstance(r, Err):
            code, _, _ = _normalize_err(r.error)
            counts[code] = counts.get(code, 0) + 1
    return MappingProxyType(counts)


def fold_error_report(
    stream: Iterable[Result[Any, E]],
    *,
    max_samples: int = 10,
    path_depth: int = 3,
) -> ErrReport[E]:
    total_errs = total_items = 0
    by_code: dict[str, _GroupBuilder[E]] = {}
    by_stage: dict[str, _GroupBuilder[E]] = {}
    by_path: dict[tuple[int, ...], _GroupBuilder[E]] = {}
    sum_attempts = sum_delay = 0.0
    cnt_attempts = cnt_delay = 0

    for r in stream:
        total_items += 1
        if isinstance(r, Ok):
            continue
        total_errs += 1
        e = r.error
        code, stage, path = _normalize_err(e)
        prefix = path[:path_depth]

        by_code.setdefault(code, _GroupBuilder(max_samples)).add(e)
        by_stage.setdefault(stage, _GroupBuilder(max_samples)).add(e)
        by_path.setdefault(prefix, _GroupBuilder(max_samples)).add(e)

        ctx = getattr(e, "ctx", None)
        if isinstance(ctx, Mapping):
            attempt = ctx.get("attempt")
            if isinstance(attempt, (int, float)):
                sum_attempts += float(attempt)
                cnt_attempts += 1
            delay = ctx.get("next_delay_ms")
            if isinstance(delay, (int, float)):
                sum_delay += float(delay)
                cnt_delay += 1

    ctx_summary: dict[str, float] = {
        "avg_attempts": (sum_attempts / cnt_attempts) if cnt_attempts else 0.0,
        "avg_next_delay_ms": (sum_delay / cnt_delay) if cnt_delay else 0.0,
        "error_rate": (total_errs / total_items) if total_items else 0.0,
    }

    return ErrReport(
        total_errs=total_errs,
        total_items=total_items,
        by_code=MappingProxyType({k: v.freeze() for k, v in by_code.items()}),
        by_stage=MappingProxyType({k: v.freeze() for k, v in by_stage.items()}),
        by_path_prefix=MappingProxyType({k: v.freeze() for k, v in by_path.items()}),
        ctx_summary=MappingProxyType(ctx_summary),
    )


def _err_to_jsonable(e: Any) -> Any:
    if isinstance(e, ErrInfo):
        d = dict(e._asdict())
        cause = d.get("cause")
        if cause is not None:
            d["cause"] = repr(cause)
        ctx = d.get("ctx")
        if isinstance(ctx, Mapping):
            d["ctx"] = dict(ctx)
        return d
    if isinstance(e, BreakInfo):
        return asdict(e)
    if hasattr(e, "_asdict"):
        try:
            return dict(e._asdict())
        except Exception:
            pass
    if is_dataclass(e) and not isinstance(e, type):
        try:
            return asdict(e)
        except Exception:
            pass
    return {"repr": repr(e)}


def report_to_jsonable(report: ErrReport[E]) -> dict[str, Any]:
    def group_to_jsonable(g: ErrGroup[E]) -> dict[str, Any]:
        return {"count": g.count, "samples": [_err_to_jsonable(e) for e in g.samples]}

    return {
        "total_errs": report.total_errs,
        "total_items": report.total_items,
        "error_rate": report.ctx_summary.get("error_rate", 0.0),
        "avg_attempts": report.ctx_summary.get("avg_attempts", 0.0),
        "avg_next_delay_ms": report.ctx_summary.get("avg_next_delay_ms", 0.0),
        "by_code": {k: group_to_jsonable(v) for k, v in report.by_code.items()},
        "by_stage": {k: group_to_jsonable(v) for k, v in report.by_stage.items()},
        "by_path_prefix": {
            ".".join(map(str, k)): group_to_jsonable(v) for k, v in report.by_path_prefix.items()
        },
    }


__all__ = ["ErrGroup", "ErrReport", "fold_error_counts", "fold_error_report", "report_to_jsonable"]
