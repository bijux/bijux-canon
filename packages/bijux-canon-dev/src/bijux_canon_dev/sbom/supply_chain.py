"""Build and verify hash-bound SBOM and provenance manifests."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess
import tarfile
import tempfile
from typing import Literal, cast
import zipfile


ArtifactKind = Literal["wheel", "sdist", "oci-image"]
SbomGenerator = Callable[["ArtifactInput", Path], Mapping[str, object]]


class SupplyChainVerificationError(RuntimeError):
    """An artifact, SBOM, or provenance binding is missing or invalid."""


@dataclass(frozen=True)
class ArtifactInput:
    """One release artifact that requires an SBOM and provenance statement."""

    kind: ArtifactKind
    path: Path


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a regular file."""
    if not path.is_file() or path.is_symlink():
        raise SupplyChainVerificationError(
            f"release input is not a regular file: {path}"
        )
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repo_path(path: Path, repo_root: Path) -> str:
    try:
        relative = path.resolve().relative_to(repo_root.resolve())
    except ValueError as exc:
        raise SupplyChainVerificationError(
            f"supply-chain input escapes the repository: {path}"
        ) from exc
    return relative.as_posix()


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SupplyChainVerificationError(
            f"invalid JSON document {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise SupplyChainVerificationError(f"JSON document must be an object: {path}")
    return cast(dict[str, object], value)


def validate_cyclonedx(document: Mapping[str, object], *, source: Path) -> int:
    """Validate the security-relevant CycloneDX structure and return component count."""
    if document.get("bomFormat") != "CycloneDX":
        raise SupplyChainVerificationError(f"SBOM is not CycloneDX: {source}")
    spec_version = document.get("specVersion")
    if spec_version not in {"1.4", "1.5", "1.6"}:
        raise SupplyChainVerificationError(
            f"SBOM has an unsupported CycloneDX version: {source}"
        )
    if (
        not isinstance(document.get("version"), int)
        or cast(int, document["version"]) < 1
    ):
        raise SupplyChainVerificationError(f"SBOM has no document version: {source}")
    components = document.get("components")
    if not isinstance(components, list) or not components:
        raise SupplyChainVerificationError(f"SBOM has no components: {source}")
    for component in components:
        if not isinstance(component, dict):
            raise SupplyChainVerificationError(
                f"SBOM contains a non-object component: {source}"
            )
        if not isinstance(component.get("name"), str) or not component["name"]:
            raise SupplyChainVerificationError(
                f"SBOM component has no package identity: {source}"
            )
        if not isinstance(component.get("type"), str) or not component["type"]:
            raise SupplyChainVerificationError(
                f"SBOM component has no package type: {source}"
            )
    return len(components)


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _provenance_statement(
    *,
    artifact: ArtifactInput,
    artifact_sha256: str,
    sbom_sha256: str,
    source_commit: str,
    resolved_identities: Mapping[str, str],
    builder_id: str,
    build_environment: Mapping[str, str],
) -> dict[str, object]:
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {"name": artifact.path.name, "digest": {"sha256": artifact_sha256}}
        ],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": f"https://bijux.io/build/{artifact.kind}/v1",
                "externalParameters": {"source_commit": source_commit},
                "internalParameters": {
                    "sbom_format": "CycloneDX JSON",
                    "sbom_sha256": sbom_sha256,
                },
                "resolvedDependencies": [
                    {"uri": name, "digest": {"sha256": digest}}
                    for name, digest in sorted(resolved_identities.items())
                ],
            },
            "runDetails": {
                "builder": {"id": builder_id},
                "metadata": {
                    "build_environment": dict(sorted(build_environment.items())),
                    "invocationId": f"local:{source_commit}:{artifact_sha256}",
                },
            },
        },
    }


def build_supply_chain_manifest(
    *,
    repo_root: Path,
    source_commit: str,
    artifacts: Sequence[ArtifactInput],
    lock_paths: Sequence[Path],
    sbom_dir: Path,
    attestation_dir: Path,
    sbom_generator: SbomGenerator,
    builder_id: str,
    container_definitions: Sequence[Path] = (),
    redistribution_evidence: Sequence[Path] = (),
    security_evidence: Sequence[Path] = (),
) -> dict[str, object]:
    """Generate, bind, and verify SBOM/provenance records for release inputs."""
    if len(source_commit) != 40 or any(
        char not in "0123456789abcdef" for char in source_commit
    ):
        raise SupplyChainVerificationError(
            "source commit must be a lowercase full Git SHA"
        )
    if not artifacts:
        raise SupplyChainVerificationError("at least one release artifact is required")
    if not lock_paths:
        raise SupplyChainVerificationError("at least one governing lock is required")

    artifact_names = [item.path.name for item in artifacts]
    if len(artifact_names) != len(set(artifact_names)):
        raise SupplyChainVerificationError("release artifact names must be unique")
    if container_definitions and not any(
        item.kind == "oci-image" for item in artifacts
    ):
        raise SupplyChainVerificationError(
            "OCI container definitions exist but no OCI image artifact was supplied"
        )

    lock_identities = {
        _repo_path(path, repo_root): sha256_file(path) for path in lock_paths
    }
    container_definition_identities = {
        _repo_path(path, repo_root): sha256_file(path) for path in container_definitions
    }
    redistribution_evidence_identities = {
        _repo_path(path, repo_root): sha256_file(path)
        for path in redistribution_evidence
    }
    security_evidence_identities = {
        _repo_path(path, repo_root): sha256_file(path) for path in security_evidence
    }
    build_environment = {
        "machine": platform.machine(),
        "operating_system": platform.platform(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
    }
    resolved_identities = (
        lock_identities
        | container_definition_identities
        | redistribution_evidence_identities
        | security_evidence_identities
    )
    records: list[dict[str, object]] = []
    for artifact in sorted(artifacts, key=lambda item: (item.kind, item.path.name)):
        artifact_sha256 = sha256_file(artifact.path)
        sbom_path = sbom_dir / f"{artifact.path.name}.cdx.json"
        sbom_document = dict(sbom_generator(artifact, sbom_path))
        _write_json(sbom_path, sbom_document)
        component_count = validate_cyclonedx(sbom_document, source=sbom_path)
        sbom_sha256 = sha256_file(sbom_path)
        statement = _provenance_statement(
            artifact=artifact,
            artifact_sha256=artifact_sha256,
            sbom_sha256=sbom_sha256,
            source_commit=source_commit,
            resolved_identities=resolved_identities,
            builder_id=builder_id,
            build_environment=build_environment,
        )
        attestation_path = attestation_dir / f"{artifact.path.name}.intoto.json"
        _write_json(attestation_path, statement)
        records.append(
            {
                "kind": artifact.kind,
                "name": artifact.path.name,
                "path": _repo_path(artifact.path, repo_root),
                "sha256": artifact_sha256,
                "byte_length": artifact.path.stat().st_size,
                "sbom_path": _repo_path(sbom_path, repo_root),
                "sbom_sha256": sbom_sha256,
                "sbom_component_count": component_count,
                "attestation_path": _repo_path(attestation_path, repo_root),
                "attestation_sha256": sha256_file(attestation_path),
            }
        )

    manifest: dict[str, object] = {
        "schema_version": "bijux.canon.supply_chain_manifest.v1",
        "source_commit": source_commit,
        "builder_id": builder_id,
        "build_environment": build_environment,
        "lock_identities": lock_identities,
        "container_definition_identities": container_definition_identities,
        "redistribution_evidence_identities": redistribution_evidence_identities,
        "security_evidence_identities": security_evidence_identities,
        "artifact_records": records,
    }
    verify_supply_chain_manifest(
        manifest, repo_root=repo_root, expected_source_commit=source_commit
    )
    return manifest


def _string_map(value: object, *, field: str) -> dict[str, str]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise SupplyChainVerificationError(f"manifest field {field} is invalid")
    return cast(dict[str, str], value)


def _object(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SupplyChainVerificationError(f"manifest field {field} is invalid")
    return cast(dict[str, object], value)


def verify_supply_chain_manifest(
    manifest: Mapping[str, object],
    *,
    repo_root: Path,
    expected_source_commit: str | None = None,
) -> None:
    """Fail closed when a manifest no longer matches its locks or release inputs."""
    if manifest.get("schema_version") != "bijux.canon.supply_chain_manifest.v1":
        raise SupplyChainVerificationError("unsupported supply-chain manifest schema")
    source_commit = manifest.get("source_commit")
    if not isinstance(source_commit, str):
        raise SupplyChainVerificationError("manifest source commit is invalid")
    if expected_source_commit is not None and source_commit != expected_source_commit:
        raise SupplyChainVerificationError("source commit mismatch")
    for relative, expected in _string_map(
        manifest.get("lock_identities"), field="lock_identities"
    ).items():
        if sha256_file(repo_root / relative) != expected:
            raise SupplyChainVerificationError(f"lock digest mismatch: {relative}")
    container_definition_identities = _string_map(
        manifest.get("container_definition_identities"),
        field="container_definition_identities",
    )
    for relative, expected in container_definition_identities.items():
        if sha256_file(repo_root / relative) != expected:
            raise SupplyChainVerificationError(
                f"container definition digest mismatch: {relative}"
            )
    redistribution_evidence_identities = _string_map(
        manifest.get("redistribution_evidence_identities"),
        field="redistribution_evidence_identities",
    )
    security_evidence_identities = _string_map(
        manifest.get("security_evidence_identities"),
        field="security_evidence_identities",
    )
    for label, identities in (
        ("redistribution evidence", redistribution_evidence_identities),
        ("security evidence", security_evidence_identities),
    ):
        for relative, expected in identities.items():
            if sha256_file(repo_root / relative) != expected:
                raise SupplyChainVerificationError(
                    f"{label} digest mismatch: {relative}"
                )

    records = manifest.get("artifact_records")
    if not isinstance(records, list) or not records:
        raise SupplyChainVerificationError("manifest has no artifact records")
    seen_names: set[str] = set()
    for value in records:
        if not isinstance(value, dict):
            raise SupplyChainVerificationError("manifest artifact record is invalid")
        record = cast(dict[str, object], value)
        name = record.get("name")
        if not isinstance(name, str):
            raise SupplyChainVerificationError("manifest artifact name is invalid")
        if name in seen_names:
            raise SupplyChainVerificationError(f"duplicate artifact record: {name}")
        seen_names.add(name)
        if record.get("kind") not in {"wheel", "sdist", "oci-image"}:
            raise SupplyChainVerificationError(f"invalid artifact kind: {name}")
        paths: dict[str, Path] = {}
        for field in ("path", "sbom_path", "attestation_path"):
            record_path = record.get(field)
            if not isinstance(record_path, str):
                raise SupplyChainVerificationError(f"manifest field {field} is invalid")
            pure = PurePosixPath(record_path)
            if pure.is_absolute() or ".." in pure.parts or "\\" in record_path:
                raise SupplyChainVerificationError(
                    f"unsafe manifest path: {record_path}"
                )
            paths[field] = repo_root / record_path
        if paths["path"].name != name:
            raise SupplyChainVerificationError(f"artifact name/path mismatch: {name}")
        for field, digest_field in (
            ("path", "sha256"),
            ("sbom_path", "sbom_sha256"),
            ("attestation_path", "attestation_sha256"),
        ):
            expected_digest = record.get(digest_field)
            if (
                not isinstance(expected_digest, str)
                or sha256_file(paths[field]) != expected_digest
            ):
                raise SupplyChainVerificationError(f"{digest_field} mismatch: {name}")

        sbom = _load_json_object(paths["sbom_path"])
        validate_cyclonedx(sbom, source=paths["sbom_path"])
        statement = _load_json_object(paths["attestation_path"])
        expected_subject = [{"name": name, "digest": {"sha256": record["sha256"]}}]
        if statement.get("_type") != "https://in-toto.io/Statement/v1":
            raise SupplyChainVerificationError(f"attestation type mismatch: {name}")
        if statement.get("predicateType") != "https://slsa.dev/provenance/v1":
            raise SupplyChainVerificationError(f"provenance type mismatch: {name}")
        if statement.get("subject") != expected_subject:
            raise SupplyChainVerificationError(f"attestation subject mismatch: {name}")
        predicate = _object(statement.get("predicate"), field="predicate")
        definition = _object(
            predicate.get("buildDefinition"), field="predicate.buildDefinition"
        )
        external = _object(
            definition.get("externalParameters"),
            field="predicate.buildDefinition.externalParameters",
        )
        internal = _object(
            definition.get("internalParameters"),
            field="predicate.buildDefinition.internalParameters",
        )
        if external.get("source_commit") != source_commit:
            raise SupplyChainVerificationError(f"provenance source mismatch: {name}")
        if internal.get("sbom_sha256") != record.get("sbom_sha256"):
            raise SupplyChainVerificationError(f"provenance SBOM mismatch: {name}")
        build_environment = _string_map(
            manifest.get("build_environment"), field="build_environment"
        )
        expected_dependencies = [
            {"uri": path, "digest": {"sha256": digest}}
            for path, digest in sorted(
                (
                    _string_map(
                        manifest.get("lock_identities"), field="lock_identities"
                    )
                    | container_definition_identities
                    | redistribution_evidence_identities
                    | security_evidence_identities
                ).items()
            )
        ]
        if definition.get("resolvedDependencies") != expected_dependencies:
            raise SupplyChainVerificationError(f"provenance lock mismatch: {name}")
        run_details = _object(predicate.get("runDetails"), field="predicate.runDetails")
        builder = _object(
            run_details.get("builder"), field="predicate.runDetails.builder"
        )
        if builder.get("id") != manifest.get("builder_id"):
            raise SupplyChainVerificationError(f"provenance builder mismatch: {name}")
        metadata = _object(
            run_details.get("metadata"), field="predicate.runDetails.metadata"
        )
        if metadata.get("build_environment") != build_environment:
            raise SupplyChainVerificationError(
                f"provenance build environment mismatch: {name}"
            )


def discover_container_definitions(repo_root: Path) -> tuple[Path, ...]:
    """Return tracked-style container build definitions outside disposable outputs."""
    definitions: set[Path] = set()
    for pattern in ("Dockerfile*", "Containerfile*"):
        definitions.update(
            path
            for path in repo_root.rglob(pattern)
            if "artifacts" not in path.relative_to(repo_root).parts
            and ".git" not in path.relative_to(repo_root).parts
        )
    return tuple(sorted(definitions))


def discover_redistribution_evidence(repo_root: Path) -> tuple[Path, ...]:
    """Return legal records governing bundled code and redistributed corpora."""
    evidence = {repo_root / "LICENSE", repo_root / "NOTICE"}
    for pattern in (
        "examples/*/corpus.lock.json",
        "examples/*/corpus-manifest.json",
        "examples/*/corpus/corpus-manifest.json",
        "examples/*/acquisition-receipts/*.json",
    ):
        evidence.update(repo_root.glob(pattern))
    return tuple(sorted(path for path in evidence if path.is_file()))


def _safe_wheel_members(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                member = PurePosixPath(name)
                if member.is_absolute() or ".." in member.parts or "\\" in name:
                    raise SupplyChainVerificationError(
                        f"unsafe wheel member in {path.name}: {name}"
                    )
    except zipfile.BadZipFile as exc:
        raise SupplyChainVerificationError(f"invalid wheel archive: {path}") from exc


def _safe_sdist_members(path: Path) -> None:
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            for member in archive.getmembers():
                name = member.name
                pure = PurePosixPath(name)
                if (
                    pure.is_absolute()
                    or ".." in pure.parts
                    or "\\" in name
                    or member.issym()
                    or member.islnk()
                    or member.isdev()
                ):
                    raise SupplyChainVerificationError(
                        f"unsafe sdist member in {path.name}: {name}"
                    )
    except tarfile.TarError as exc:
        raise SupplyChainVerificationError(f"invalid sdist archive: {path}") from exc


def external_sbom_generator(
    *, extract_root: Path, syft: str, cyclonedx: str
) -> SbomGenerator:
    """Create a generator backed by Syft plus CycloneDX schema validation."""

    def generate(artifact: ArtifactInput, output: Path) -> Mapping[str, object]:
        def run_scan(scan_target: str) -> None:
            output.parent.mkdir(parents=True, exist_ok=True)
            scan = subprocess.run(
                [
                    syft,
                    "scan",
                    scan_target,
                    "-o",
                    f"cyclonedx-json={output}",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if scan.returncode:
                raise SupplyChainVerificationError(
                    scan.stderr or scan.stdout or "Syft failed"
                )

        if artifact.kind in {"wheel", "sdist"}:
            extract_root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                prefix=f"{artifact.path.stem}-", dir=extract_root
            ) as extracted_name:
                extracted = Path(extracted_name)
                if artifact.kind == "wheel":
                    _safe_wheel_members(artifact.path)
                    with zipfile.ZipFile(artifact.path) as wheel_archive:
                        wheel_archive.extractall(extracted)
                else:
                    _safe_sdist_members(artifact.path)
                    with tarfile.open(artifact.path, mode="r:gz") as sdist_archive:
                        sdist_archive.extractall(extracted, filter="data")
                run_scan(f"dir:{extracted}")
        else:
            run_scan(f"oci-archive:{artifact.path}")
        validation = subprocess.run(
            [
                cyclonedx,
                "validate",
                "--input-format",
                "json",
                "--input-file",
                str(output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if validation.returncode:
            raise SupplyChainVerificationError(
                validation.stderr or validation.stdout or "CycloneDX validation failed"
            )
        return _load_json_object(output)

    return generate


def _git_head(repo_root: Path) -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise SupplyChainVerificationError(
            "refusing provenance generation from a dirty source tree"
        )
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse supply-chain manifest command arguments."""
    parser = argparse.ArgumentParser(
        description="Generate and verify SBOM/provenance for release artifacts."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--oci-image", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--lock", type=Path, action="append", default=[])
    parser.add_argument("--security-evidence", type=Path, action="append", default=[])
    parser.add_argument("--syft", default="syft")
    parser.add_argument("--cyclonedx", default="cyclonedx")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Generate a release supply-chain manifest from all discovered artifacts."""
    args = parse_args(argv)
    repo_root = cast(Path, args.repo_root).resolve()
    wheel_dir = cast(Path, args.wheel_dir)
    wheels = tuple(sorted(wheel_dir.glob("*.whl")))
    sdists = tuple(sorted(wheel_dir.glob("*.tar.gz")))
    artifacts = (
        tuple(ArtifactInput("wheel", path) for path in wheels)
        + tuple(ArtifactInput("sdist", path) for path in sdists)
        + tuple(
            ArtifactInput("oci-image", path)
            for path in cast(list[Path], args.oci_image)
        )
    )
    output_dir = cast(Path, args.output_dir)
    locks = tuple(cast(list[Path], args.lock)) or (
        repo_root / "uv.lock",
        repo_root / "pyproject.toml",
    )
    manifest = build_supply_chain_manifest(
        repo_root=repo_root,
        source_commit=_git_head(repo_root),
        artifacts=artifacts,
        lock_paths=locks,
        sbom_dir=output_dir / "sboms",
        attestation_dir=output_dir / "attestations",
        sbom_generator=external_sbom_generator(
            extract_root=output_dir / "extracted",
            syft=args.syft,
            cyclonedx=args.cyclonedx,
        ),
        builder_id="https://github.com/bijux/bijux-canon/supply-chain",
        container_definitions=discover_container_definitions(repo_root),
        redistribution_evidence=discover_redistribution_evidence(repo_root),
        security_evidence=tuple(cast(list[Path], args.security_evidence)),
    )
    _write_json(cast(Path, args.manifest), manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
