# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed metadata predicates shared by lexical and dense retrieval."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
import math
from types import MappingProxyType
from typing import TypeAlias

MetadataScalar: TypeAlias = str | int | float | bool | None
MetadataValue: TypeAlias = MetadataScalar | tuple[str, ...]

GOVERNED_METADATA_FIELDS = (
    "date",
    "doi",
    "format",
    "language",
    "path",
    "section",
    "source_id",
    "tags",
)
_RESERVED_FIELDS = frozenset(GOVERNED_METADATA_FIELDS)


def validated_metadata(
    metadata: Mapping[str, MetadataValue | Sequence[str]],
) -> Mapping[str, MetadataValue]:
    """Return immutable canonical JSON metadata accepted by every backend."""

    result: dict[str, MetadataValue] = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or not key:
            raise ValueError("index metadata keys must be non-empty strings")
        if isinstance(value, list | tuple):
            if key in _RESERVED_FIELDS - {"tags"}:
                raise ValueError(f"governed metadata field {key!r} requires a string")
            if any(not isinstance(item, str) or not item for item in value):
                raise ValueError(
                    "index metadata collections must contain non-empty strings"
                )
            result[key] = tuple(sorted(set(value)))
            continue
        if not isinstance(value, str | int | float | bool | None):
            raise ValueError(
                "index metadata values must be JSON scalars or string collections"
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("index metadata numbers must be finite")
        if key in _RESERVED_FIELDS - {"tags"} and (
            not isinstance(value, str) or not value
        ):
            raise ValueError(f"governed metadata field {key!r} requires a string")
        if key == "date" and isinstance(value, str):
            try:
                date.fromisoformat(value)
            except ValueError as error:
                raise ValueError("governed metadata date must use ISO 8601") from error
        if key == "tags" and isinstance(value, str):
            value = (value,)
        result[key] = value
    return MappingProxyType(dict(sorted(result.items())))


class MetadataOperator(StrEnum):
    """Supported comparisons for caller-owned metadata fields."""

    equal = "equal"
    not_equal = "not_equal"
    one_of = "one_of"
    contains = "contains"
    greater_or_equal = "greater_or_equal"
    less_or_equal = "less_or_equal"
    exists = "exists"
    absent = "absent"


@dataclass(frozen=True, slots=True)
class UserMetadataPredicate:
    """One typed predicate over a non-reserved caller metadata key."""

    key: str
    operator: MetadataOperator
    value: MetadataValue | tuple[MetadataScalar, ...] | None = None

    def __post_init__(self) -> None:
        if not self.key or self.key in _RESERVED_FIELDS:
            raise ValueError("user metadata predicates require a non-reserved key")
        if not isinstance(self.operator, MetadataOperator):
            raise ValueError("user metadata predicate operator is unsupported")
        if self.operator in {MetadataOperator.exists, MetadataOperator.absent}:
            if self.value is not None:
                raise ValueError("existence predicates must not contain a value")
            return
        if self.value is None:
            raise ValueError("comparison predicates require a value")
        if self.operator is MetadataOperator.one_of:
            if not isinstance(self.value, tuple) or not self.value:
                raise ValueError("one_of predicates require a non-empty tuple")
            for value in self.value:
                _validate_comparison_value(value)
            return
        _validate_comparison_value(self.value)


def _validate_comparison_value(value: object) -> None:
    if isinstance(value, tuple):
        if any(not isinstance(item, str) or not item for item in value):
            raise ValueError("metadata comparison collections require strings")
        return
    if not isinstance(value, str | int | float | bool):
        raise ValueError("metadata comparison values must be non-null JSON scalars")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("metadata comparison numbers must be finite")


def _validated_choices(name: str, values: Sequence[str]) -> tuple[str, ...]:
    choices = tuple(values)
    if any(not isinstance(value, str) or not value for value in choices):
        raise ValueError(f"{name} filters require non-empty strings")
    return tuple(sorted(set(choices)))


@dataclass(frozen=True, slots=True)
class MetadataFilter:
    """Conjunctive typed filter for governed and caller-owned metadata."""

    source_ids: tuple[str, ...] = ()
    dois: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    formats: tuple[str, ...] = ()
    sections: tuple[str, ...] = ()
    date_from: date | None = None
    date_to: date | None = None
    tags: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    user: tuple[UserMetadataPredicate, ...] = ()
    match_none: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.match_none, bool):
            raise ValueError("metadata match_none must be boolean")
        for field_name in (
            "source_ids",
            "dois",
            "paths",
            "formats",
            "sections",
            "tags",
            "languages",
        ):
            object.__setattr__(
                self,
                field_name,
                _validated_choices(field_name, getattr(self, field_name)),
            )
        if self.date_from is not None and not isinstance(self.date_from, date):
            raise ValueError("date_from must be a date")
        if self.date_to is not None and not isinstance(self.date_to, date):
            raise ValueError("date_to must be a date")
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("metadata date range is reversed")
        if any(
            not isinstance(predicate, UserMetadataPredicate) for predicate in self.user
        ):
            raise ValueError("user filters must be typed metadata predicates")


def _matches_choices(
    metadata: Mapping[str, MetadataValue], key: str, choices: tuple[str, ...]
) -> bool:
    if not choices:
        return True
    value = metadata.get(key)
    return isinstance(value, str) and value in choices


def _matches_tags(metadata: Mapping[str, MetadataValue], tags: tuple[str, ...]) -> bool:
    if not tags:
        return True
    value = metadata.get("tags")
    if isinstance(value, str):
        admitted = {value}
    elif isinstance(value, tuple):
        admitted = set(value)
    else:
        return False
    return set(tags).issubset(admitted)


def _matches_date(metadata: Mapping[str, MetadataValue], spec: MetadataFilter) -> bool:
    if spec.date_from is None and spec.date_to is None:
        return True
    value = metadata.get("date")
    if not isinstance(value, str):
        return False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    if spec.date_from is not None and parsed < spec.date_from:
        return False
    return spec.date_to is None or parsed <= spec.date_to


def _ordered_compare(left: object, right: object, *, greater: bool) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    if isinstance(left, int | float) and isinstance(right, int | float):
        return left >= right if greater else left <= right
    if isinstance(left, str) and isinstance(right, str):
        return left >= right if greater else left <= right
    return False


def _matches_user_predicate(
    metadata: Mapping[str, MetadataValue], predicate: UserMetadataPredicate
) -> bool:
    exists = predicate.key in metadata
    if predicate.operator is MetadataOperator.exists:
        return exists
    if predicate.operator is MetadataOperator.absent:
        return not exists
    if not exists:
        return False
    actual = metadata[predicate.key]
    expected = predicate.value
    if predicate.operator is MetadataOperator.equal:
        return actual == expected
    if predicate.operator is MetadataOperator.not_equal:
        return actual != expected
    if predicate.operator is MetadataOperator.one_of:
        return isinstance(expected, tuple) and actual in expected
    if predicate.operator is MetadataOperator.contains:
        if isinstance(actual, tuple):
            return expected in actual
        return (
            isinstance(actual, str) and isinstance(expected, str) and expected in actual
        )
    return _ordered_compare(
        actual,
        expected,
        greater=predicate.operator is MetadataOperator.greater_or_equal,
    )


def matches_metadata_filter(
    metadata: Mapping[str, MetadataValue], spec: MetadataFilter
) -> bool:
    """Evaluate one filter identically for every retrieval channel."""

    choices = (
        ("source_id", spec.source_ids),
        ("doi", spec.dois),
        ("path", spec.paths),
        ("format", spec.formats),
        ("section", spec.sections),
        ("language", spec.languages),
    )
    return (
        not spec.match_none
        and all(_matches_choices(metadata, key, values) for key, values in choices)
        and _matches_date(metadata, spec)
        and _matches_tags(metadata, spec.tags)
        and all(_matches_user_predicate(metadata, predicate) for predicate in spec.user)
    )


__all__ = [
    "GOVERNED_METADATA_FIELDS",
    "MetadataFilter",
    "MetadataOperator",
    "MetadataScalar",
    "MetadataValue",
    "UserMetadataPredicate",
    "matches_metadata_filter",
    "validated_metadata",
]
