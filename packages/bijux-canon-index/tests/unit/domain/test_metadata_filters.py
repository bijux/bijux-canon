# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for typed metadata predicates shared by retrieval channels."""

from __future__ import annotations

from datetime import date

import pytest

from bijux_canon_index.domain.metadata_filters import (
    MetadataFilter,
    MetadataOperator,
    UserMetadataPredicate,
    matches_metadata_filter,
    validated_metadata,
)


def _metadata() -> dict[str, object]:
    return {
        "source_id": "plos-pone-0256353",
        "doi": "10.1371/journal.pone.0256353",
        "path": "objects/plos-pone-0256353/article.xml",
        "format": "jats",
        "section": "results",
        "date": "2021-09-01",
        "tags": ("ancient-dna", "reviewed"),
        "language": "en",
        "quality": 0.95,
        "license": "CC-BY-4.0",
        "note": "manually reviewed evidence",
    }


def test_governed_and_user_predicates_match_conjunctively() -> None:
    metadata = validated_metadata(_metadata())  # type: ignore[arg-type]
    spec = MetadataFilter(
        source_ids=("plos-pone-0256353",),
        dois=("10.1371/journal.pone.0256353",),
        paths=("objects/plos-pone-0256353/article.xml",),
        formats=("jats",),
        sections=("results",),
        date_from=date(2021, 1, 1),
        date_to=date(2021, 12, 31),
        tags=("reviewed", "ancient-dna"),
        languages=("en",),
        user=(
            UserMetadataPredicate(
                "quality", MetadataOperator.greater_or_equal, 0.9
            ),
            UserMetadataPredicate(
                "license", MetadataOperator.one_of, ("CC0-1.0", "CC-BY-4.0")
            ),
            UserMetadataPredicate("note", MetadataOperator.contains, "reviewed"),
            UserMetadataPredicate("retracted", MetadataOperator.absent),
        ),
    )

    assert matches_metadata_filter(metadata, spec)
    assert not matches_metadata_filter(
        metadata, MetadataFilter(tags=("counterevidence",))
    )


@pytest.mark.parametrize(
    ("predicate", "expected"),
    [
        (UserMetadataPredicate("quality", MetadataOperator.equal, 0.95), True),
        (UserMetadataPredicate("quality", MetadataOperator.not_equal, 0.1), True),
        (UserMetadataPredicate("quality", MetadataOperator.less_or_equal, 1.0), True),
        (UserMetadataPredicate("quality", MetadataOperator.greater_or_equal, 1.0), False),
        (UserMetadataPredicate("license", MetadataOperator.exists), True),
        (UserMetadataPredicate("license", MetadataOperator.absent), False),
        (UserMetadataPredicate("tags_local", MetadataOperator.contains, "x"), False),
    ],
)
def test_user_predicate_operators(
    predicate: UserMetadataPredicate, expected: bool
) -> None:
    metadata = validated_metadata(_metadata())  # type: ignore[arg-type]

    assert matches_metadata_filter(metadata, MetadataFilter(user=(predicate,))) is expected


def test_invalid_filters_fail_during_construction() -> None:
    with pytest.raises(ValueError, match="reversed"):
        MetadataFilter(date_from=date(2024, 1, 1), date_to=date(2023, 1, 1))
    with pytest.raises(ValueError, match="non-reserved"):
        UserMetadataPredicate("doi", MetadataOperator.equal, "value")
    with pytest.raises(ValueError, match="must not contain"):
        UserMetadataPredicate("license", MetadataOperator.exists, "value")
    with pytest.raises(ValueError, match="non-empty tuple"):
        UserMetadataPredicate("license", MetadataOperator.one_of, ())


def test_metadata_string_collections_are_canonical_sets() -> None:
    metadata = validated_metadata({"tags": ["reviewed", "ancient-dna", "reviewed"]})

    assert metadata["tags"] == ("ancient-dna", "reviewed")


def test_governed_metadata_types_fail_closed() -> None:
    with pytest.raises(ValueError, match="requires a string"):
        validated_metadata({"doi": 42})
    with pytest.raises(ValueError, match="ISO 8601"):
        validated_metadata({"date": "September 2021"})
    assert validated_metadata({"tags": "reviewed"})["tags"] == ("reviewed",)
