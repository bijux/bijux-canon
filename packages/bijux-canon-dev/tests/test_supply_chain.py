from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import stat
import subprocess
import tarfile
from typing import cast
import zipfile

import pytest

from bijux_canon_dev.sbom.supply_chain import (
    ArtifactInput,
    SupplyChainVerificationError,
    build_supply_chain_manifest,
    discover_container_definitions,
    discover_redistribution_evidence,
    external_sbom_generator,
    sha256_file,
    validate_cyclonedx,
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
    assert manifest["build_environment"]
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


def test_manifest_binds_redistribution_and_security_evidence(tmp_path: Path) -> None:
    root, lock, wheel = _repository(tmp_path)
    redistribution = root / "LICENSE"
    security = root / "artifacts" / "secret-scan.json"
    redistribution.write_text("Apache-2.0\n", encoding="utf-8")
    security.write_text('{"result":"passed"}\n', encoding="utf-8")

    manifest = build_supply_chain_manifest(
        repo_root=root,
        source_commit=SOURCE_COMMIT,
        artifacts=[ArtifactInput("wheel", wheel)],
        lock_paths=[lock],
        sbom_dir=root / "artifacts" / "release" / "sboms",
        attestation_dir=root / "artifacts" / "release" / "attestations",
        sbom_generator=_sbom,
        builder_id="https://bijux.invalid/test-builder",
        redistribution_evidence=[redistribution],
        security_evidence=[security],
    )

    assert manifest["redistribution_evidence_identities"] == {
        "LICENSE": sha256_file(redistribution)
    }
    assert manifest["security_evidence_identities"] == {
        "artifacts/secret-scan.json": sha256_file(security)
    }
    security.write_text('{"result":"changed"}\n', encoding="utf-8")
    with pytest.raises(SupplyChainVerificationError, match="security evidence digest"):
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


def test_container_discovery_prunes_repository_metadata_and_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, list[str]] = {}

    def fake_walk(_root: Path) -> object:
        directories = ["artifacts", ".git", "src"]
        yield str(tmp_path), directories, []
        observed["root_directories"] = list(directories)
        yield str(tmp_path / "src"), [], ["Dockerfile.runtime", "module.py"]

    monkeypatch.setattr("bijux_canon_dev.sbom.supply_chain.os.walk", fake_walk)

    definitions = discover_container_definitions(tmp_path)

    assert observed == {"root_directories": ["src"]}
    assert definitions == (tmp_path / "src" / "Dockerfile.runtime",)


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


def test_manifest_covers_source_distributions(tmp_path: Path) -> None:
    root, lock, _wheel = _repository(tmp_path)
    sdist = root / "artifacts" / "release" / "dist" / "bijux-canon-1.0.tar.gz"
    sdist.write_bytes(b"source distribution")

    manifest = _manifest(root, lock, [ArtifactInput("sdist", sdist)])

    record = cast(list[dict[str, object]], manifest["artifact_records"])[0]
    assert record["kind"] == "sdist"


def test_external_generator_rejects_wheel_path_traversal(tmp_path: Path) -> None:
    wheel = tmp_path / "malicious.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("../escape.py", "owned")
    generator = external_sbom_generator(
        extract_root=tmp_path / "extract", syft="syft", cyclonedx="cyclonedx"
    )

    with pytest.raises(SupplyChainVerificationError, match="unsafe wheel member"):
        generator(ArtifactInput("wheel", wheel), tmp_path / "output.json")


def test_external_generator_rejects_wheel_links(tmp_path: Path) -> None:
    wheel = tmp_path / "malicious.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        member = zipfile.ZipInfo("package/link")
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(member, "../../outside")
    generator = external_sbom_generator(
        extract_root=tmp_path / "extract", syft="syft", cyclonedx="cyclonedx"
    )

    with pytest.raises(SupplyChainVerificationError, match="unsafe wheel member"):
        generator(ArtifactInput("wheel", wheel), tmp_path / "output.json")


def test_external_generator_streams_validated_wheel_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "package.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("package/module.py", "VALUE = 1\n")
        archive.writestr(
            "package-1.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: package\nVersion: 1.0\n",
        )

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if command[0] == "syft":
            scan_root = Path(command[2].removeprefix("dir:"))
            assert (scan_root / "package" / "module.py").read_text(
                encoding="utf-8"
            ) == "VALUE = 1\n"
            output = Path(command[-1].split("=", maxsplit=1)[1])
            output.write_text(json.dumps(_sbom(ArtifactInput("wheel", wheel), output)))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("bijux_canon_dev.sbom.supply_chain.subprocess.run", fake_run)
    output = tmp_path / "output.json"
    generator = external_sbom_generator(
        extract_root=tmp_path / "extract", syft="syft", cyclonedx="cyclonedx"
    )

    assert generator(ArtifactInput("wheel", wheel), output)["bomFormat"] == "CycloneDX"


def test_external_generator_binds_wheel_hash_to_existing_distribution_component(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "package-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "package-1.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: package\nVersion: 1.0\n",
        )

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if command[0] == "syft":
            output_path = Path(command[-1].split("=", maxsplit=1)[1])
            output_path.write_text(
                json.dumps(
                    {
                        "bomFormat": "CycloneDX",
                        "specVersion": "1.6",
                        "version": 1,
                        "components": [
                            {
                                "bom-ref": "syft-package-id",
                                "name": "package",
                                "purl": "pkg:pypi/package@1.0",
                                "type": "library",
                                "version": "1.0",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("bijux_canon_dev.sbom.supply_chain.subprocess.run", fake_run)
    output = tmp_path / "output.json"
    generator = external_sbom_generator(
        extract_root=tmp_path / "extract", syft="syft", cyclonedx="cyclonedx"
    )

    document = generator(ArtifactInput("wheel", wheel), output)

    components = cast(list[dict[str, object]], document["components"])
    assert components == [
        {
            "bom-ref": "syft-package-id",
            "hashes": [{"alg": "SHA-256", "content": sha256_file(wheel)}],
            "name": "package",
            "purl": "pkg:pypi/package@1.0",
            "type": "library",
            "version": "1.0",
        }
    ]


def test_external_generator_adds_sdist_identity_when_syft_finds_no_components(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sdist = tmp_path / "example_package-1.2.3.tar.gz"
    metadata = b"Metadata-Version: 2.4\nName: example-package\nVersion: 1.2.3\n"
    with tarfile.open(sdist, mode="w:gz") as archive:
        member = tarfile.TarInfo("example_package-1.2.3/PKG-INFO")
        member.size = len(metadata)
        archive.addfile(member, io.BytesIO(metadata))

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if command[0] == "syft":
            output_path = Path(command[-1].split("=", maxsplit=1)[1])
            output_path.write_text(
                json.dumps(
                    {
                        "bomFormat": "CycloneDX",
                        "specVersion": "1.6",
                        "version": 1,
                        "components": [],
                    }
                ),
                encoding="utf-8",
            )
        if command[0] == "cyclonedx":
            output_path = Path(command[command.index("--input-file") + 1])
            document = json.loads(output_path.read_text(encoding="utf-8"))
            assert document["components"] == [
                {
                    "bom-ref": "pkg:pypi/example-package@1.2.3",
                    "hashes": [{"alg": "SHA-256", "content": sha256_file(sdist)}],
                    "name": "example-package",
                    "purl": "pkg:pypi/example-package@1.2.3",
                    "type": "library",
                    "version": "1.2.3",
                }
            ]
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("bijux_canon_dev.sbom.supply_chain.subprocess.run", fake_run)
    output = tmp_path / "output.json"
    generator = external_sbom_generator(
        extract_root=tmp_path / "extract", syft="syft", cyclonedx="cyclonedx"
    )

    document = generator(ArtifactInput("sdist", sdist), output)

    assert validate_cyclonedx(document, source=output) == 1


def test_external_generator_rejects_sdist_links(tmp_path: Path) -> None:
    sdist = tmp_path / "malicious.tar.gz"
    with tarfile.open(sdist, mode="w:gz") as archive:
        member = tarfile.TarInfo("package/link")
        member.type = tarfile.SYMTYPE
        member.linkname = "../../outside"
        archive.addfile(member, io.BytesIO())
    generator = external_sbom_generator(
        extract_root=tmp_path / "extract", syft="syft", cyclonedx="cyclonedx"
    )

    with pytest.raises(SupplyChainVerificationError, match="unsafe sdist member"):
        generator(ArtifactInput("sdist", sdist), tmp_path / "output.json")


def test_repository_redistribution_discovery_covers_all_corpus_evidence() -> None:
    repository = Path(__file__).resolve().parents[3]
    discovered = {
        path.relative_to(repository).as_posix()
        for path in discover_redistribution_evidence(repository)
    }

    assert {"LICENSE", "NOTICE"}.issubset(discovered)
    assert {
        "examples/ancient-dna-research/corpus.lock.json",
        "examples/ancient-dna-research/corpus/corpus-manifest.json",
        "examples/document-formats/corpus.lock.json",
        "examples/urban-heat-research/corpus-manifest.json",
    }.issubset(discovered)
    assert len([path for path in discovered if "/acquisition-receipts/" in path]) == 7
