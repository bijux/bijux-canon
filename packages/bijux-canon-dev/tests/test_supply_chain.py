from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import cast
import zipfile

import pytest

from bijux_canon_dev.sbom.supply_chain import (
    ArtifactInput,
    SupplyChainVerificationError,
    build_supply_chain_manifest,
    external_sbom_generator,
    sha256_file,
    verify_supply_chain_manifest,
)


SOURCE_COMMIT = "1" * 40


def _sbom(_artifact: ArtifactInput, _output: Path) -> dict[str, object]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "components": [{"type": "library", "name": "release-component"}],
    }


def _repository(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "repo"
    dist = root / "artifacts" / "release" / "dist"
    dist.mkdir(parents=True)
    lock = root / "uv.lock"
    lock.write_text("version = 1\n", encoding="utf-8")
    wheel = dist / "bijux_canon-1.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel payload")
    return root, lock, wheel


def _manifest(
    root: Path, lock: Path, artifacts: list[ArtifactInput]
) -> dict[str, object]:
    return build_supply_chain_manifest(
        repo_root=root,
        source_commit=SOURCE_COMMIT,
        artifacts=artifacts,
        lock_paths=[lock],
        sbom_dir=root / "artifacts" / "release" / "sboms",
        attestation_dir=root / "artifacts" / "release" / "attestations",
        sbom_generator=_sbom,
        builder_id="https://bijux.invalid/test-builder",
    )


def test_manifest_binds_wheel_sbom_attestation_source_and_lock(tmp_path: Path) -> None:
    root, lock, wheel = _repository(tmp_path)

    manifest = _manifest(root, lock, [ArtifactInput("wheel", wheel)])

    assert manifest["source_commit"] == SOURCE_COMMIT
    assert manifest["container_definition_identities"] == {}
    records = cast(list[dict[str, object]], manifest["artifact_records"])
    assert records[0]["kind"] == "wheel"
    assert records[0]["sbom_component_count"] == 1
    statement = json.loads(
        (root / cast(str, records[0]["attestation_path"])).read_text(encoding="utf-8")
    )
    assert statement["subject"] == [
        {"name": wheel.name, "digest": {"sha256": records[0]["sha256"]}}
    ]
    verify_supply_chain_manifest(manifest, repo_root=root)


@pytest.mark.parametrize("target", ["artifact", "sbom", "attestation", "lock"])
def test_manifest_rejects_substitution_after_publication(
    tmp_path: Path, target: str
) -> None:
    root, lock, wheel = _repository(tmp_path)
    manifest = _manifest(root, lock, [ArtifactInput("wheel", wheel)])
    record = cast(list[dict[str, object]], manifest["artifact_records"])[0]
    paths = {
        "artifact": wheel,
        "sbom": root / cast(str, record["sbom_path"]),
        "attestation": root / cast(str, record["attestation_path"]),
        "lock": lock,
    }
    paths[target].write_bytes(paths[target].read_bytes() + b"tampered")

    with pytest.raises(SupplyChainVerificationError, match="mismatch"):
        verify_supply_chain_manifest(manifest, repo_root=root)


def test_manifest_rejects_attestation_bound_to_another_artifact(tmp_path: Path) -> None:
    root, lock, wheel = _repository(tmp_path)
    manifest = _manifest(root, lock, [ArtifactInput("wheel", wheel)])
    forged = copy.deepcopy(manifest)
    record = cast(list[dict[str, object]], forged["artifact_records"])[0]
    attestation = root / cast(str, record["attestation_path"])
    statement = json.loads(attestation.read_text(encoding="utf-8"))
    statement["subject"] = [{"name": wheel.name, "digest": {"sha256": "0" * 64}}]
    attestation.write_text(json.dumps(statement), encoding="utf-8")
    record["attestation_sha256"] = sha256_file(attestation)

    with pytest.raises(
        SupplyChainVerificationError, match="attestation subject mismatch"
    ):
        verify_supply_chain_manifest(forged, repo_root=root)


def test_container_definition_requires_a_scanned_oci_image(tmp_path: Path) -> None:
    root, lock, wheel = _repository(tmp_path)
    dockerfile = root / "Dockerfile"
    dockerfile.write_text("FROM scratch\n", encoding="utf-8")

    with pytest.raises(SupplyChainVerificationError, match="no OCI image artifact"):
        build_supply_chain_manifest(
            repo_root=root,
            source_commit=SOURCE_COMMIT,
            artifacts=[ArtifactInput("wheel", wheel)],
            lock_paths=[lock],
            sbom_dir=root / "artifacts" / "release" / "sboms",
            attestation_dir=root / "artifacts" / "release" / "attestations",
            sbom_generator=_sbom,
            builder_id="https://bijux.invalid/test-builder",
            container_definitions=[dockerfile],
        )


def test_manifest_covers_wheels_and_oci_images(tmp_path: Path) -> None:
    root, lock, wheel = _repository(tmp_path)
    image = root / "artifacts" / "release" / "image.oci.tar"
    image.write_bytes(b"oci image layout")
    dockerfile = root / "Dockerfile"
    dockerfile.write_text("FROM scratch\n", encoding="utf-8")

    manifest = build_supply_chain_manifest(
        repo_root=root,
        source_commit=SOURCE_COMMIT,
        artifacts=[ArtifactInput("wheel", wheel), ArtifactInput("oci-image", image)],
        lock_paths=[lock],
        sbom_dir=root / "artifacts" / "release" / "sboms",
        attestation_dir=root / "artifacts" / "release" / "attestations",
        sbom_generator=_sbom,
        builder_id="https://bijux.invalid/test-builder",
        container_definitions=[dockerfile],
    )

    records = cast(list[dict[str, object]], manifest["artifact_records"])
    assert {record["kind"] for record in records} == {"wheel", "oci-image"}
    identities = cast(dict[str, str], manifest["container_definition_identities"])
    assert set(identities) == {"Dockerfile"}


def test_external_generator_rejects_wheel_path_traversal(tmp_path: Path) -> None:
    wheel = tmp_path / "malicious.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("../escape.py", "owned")
    generator = external_sbom_generator(
        extract_root=tmp_path / "extract", syft="syft", cyclonedx="cyclonedx"
    )

    with pytest.raises(SupplyChainVerificationError, match="unsafe wheel member"):
        generator(ArtifactInput("wheel", wheel), tmp_path / "output.json")
