from __future__ import annotations

from dataclasses import replace

import pytest

from bijux_canon_runtime.model.artifact import (
    AddressedArtifact,
    LogicalArtifactReference,
    canonical_json_bytes,
)
from bijux_canon_runtime.ontology.ids import ArtifactID


def test_json_identity_uses_canonical_bytes_and_schema() -> None:
    first = AddressedArtifact.from_json(
        {"answer": 42, "sources": ["one", "two"]},
        schema_id="bijux.runtime.answer.v1",
        producer="bijux-canon-runtime:research",
    )
    reordered = AddressedArtifact.from_json(
        {"sources": ["one", "two"], "answer": 42},
        schema_id="bijux.runtime.answer.v1",
        producer="bijux-canon-runtime:research",
    )
    changed_schema = AddressedArtifact.from_json(
        {"answer": 42, "sources": ["one", "two"]},
        schema_id="bijux.runtime.answer.v2",
        producer="bijux-canon-runtime:research",
    )

    assert first == reordered
    assert first.descriptor.artifact_id != changed_schema.descriptor.artifact_id
    assert first.descriptor.payload_sha256 == changed_schema.descriptor.payload_sha256
    assert first.canonical_bytes == b'{"answer":42,"sources":["one","two"]}'
    assert first.descriptor.size_bytes == len(first.canonical_bytes)
    assert first.descriptor.media_type == "application/json"


def test_descriptor_retains_producer_dependencies_and_rejects_drift() -> None:
    dependency = AddressedArtifact.from_bytes(
        b"exact source text",
        schema_id="bijux.runtime.source.v1",
        media_type="text/plain",
        producer="bijux-canon-ingest:source",
    )
    derived = AddressedArtifact.from_json(
        {"source": dependency.descriptor.artifact_id},
        schema_id="bijux.runtime.derived.v1",
        producer="bijux-canon-runtime:derivation",
        dependencies=(dependency.descriptor.artifact_id,),
    )

    assert derived.descriptor.dependencies == (dependency.descriptor.artifact_id,)
    assert derived.descriptor.producer == "bijux-canon-runtime:derivation"
    with pytest.raises(ValueError, match="does not match"):
        replace(derived, canonical_bytes=b"tampered")
    with pytest.raises(ValueError, match="sorted"):
        AddressedArtifact.from_json(
            {},
            schema_id="bijux.runtime.derived.v1",
            producer="producer",
            dependencies=(
                ArtifactID("sha256:" + "f" * 64),
                ArtifactID("sha256:" + "a" * 64),
            ),
        )


def test_logical_reference_is_not_an_immutable_blob_identity() -> None:
    first = AddressedArtifact.from_json(
        {"revision": 1},
        schema_id="bijux.runtime.publication.v1",
        producer="bijux-canon-runtime:publication",
    )
    second = AddressedArtifact.from_json(
        {"revision": 2},
        schema_id="bijux.runtime.publication.v1",
        producer="bijux-canon-runtime:publication",
    )
    reference = LogicalArtifactReference.create(
        namespace="publications",
        name="ancient-dna",
        revision=0,
        target_artifact_id=first.descriptor.artifact_id,
    )
    advanced = reference.advance(second.descriptor.artifact_id)

    assert reference.logical_id == advanced.logical_id
    assert reference.target_artifact_id != advanced.target_artifact_id
    assert advanced.revision == 1
    assert not reference.logical_id.startswith("sha256:")


@pytest.mark.parametrize(
    "payload",
    [
        {1: "coerced key"},
        {"value": float("nan")},
        {"value": object()},
        ("not", "a", "JSON", "array"),
    ],
)
def test_canonical_json_rejects_ambiguous_values(payload: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        canonical_json_bytes(payload)
