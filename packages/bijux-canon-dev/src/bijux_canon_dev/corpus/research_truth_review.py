"""Create blind truth-review packets and verify independent human decisions."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Mapping, Sequence, cast

from bijux_canon_dev.corpus.acquisition import canonical

PACKET_SCHEMA = "bijux.canon.research_truth_review_packet.v1"
REVIEW_SCHEMA = "bijux.canon.research_truth_review.v1"
ADJUDICATION_SCHEMA = "bijux.canon.research_truth_adjudication.v1"
ADMISSION_SCHEMA = "bijux.canon.research_truth_review_admission.v1"
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TRUTH_FILES = {
    "claim": ("claim-truth.jsonl", "truth_id"),
    "evaluation-case": ("evaluation-cases.jsonl", "case_id"),
    "locator": ("locator-truth.jsonl", "truth_id"),
    "qrel": ("qrels.jsonl", "qrel_id"),
    "question-claim": ("question-claim-truth.jsonl", "case_id"),
    "question": ("research-questions.jsonl", "question_id"),
}
_PROVENANCE_KEYS = {
    "adjudication_status",
    "adjudicator_id",
    "label_origin",
    "review_method",
    "review_status",
    "reviewed_on",
    "reviewer_id",
}
_REVIEW_VERDICTS = {"approve", "changes-required", "reject"}
_ADJUDICATION_VERDICTS = {"admit", "reject"}


class TruthReviewError(ValueError):
    """A packet or human decision fails the bound review protocol."""


def create_truth_review_packet(
    *,
    truth_root: Path,
    corpus_lock_path: Path,
    research_root: Path,
    protocol_path: Path,
    source_commit: str,
    output_directory: Path,
) -> dict[str, object]:
    """Write one portable, reviewer-blind packet over all required truth records."""

    if _COMMIT.fullmatch(source_commit) is None:
        raise TruthReviewError("truth review source commit must be a full Git SHA")
    if output_directory.exists():
        raise TruthReviewError("truth review output directory must not already exist")
    protocol = _regular_bytes(protocol_path, "annotation protocol")
    lock_bytes = _regular_bytes(corpus_lock_path, "corpus lock")
    lock = _object(json.loads(lock_bytes), "corpus lock")
    sources = _source_manifest(lock, research_root)
    subjects: list[dict[str, object]] = []
    truth_files: dict[str, dict[str, object]] = {}
    author_ids: set[str] = set()
    for kind, (name, identity_key) in sorted(_TRUTH_FILES.items()):
        path = truth_root / name
        raw = _regular_bytes(path, f"truth file {name}")
        records = _canonical_jsonl(raw, name)
        truth_files[name] = {"row_count": len(records), "sha256": _digest_bytes(raw)}
        for record in records:
            author_ids.update(_reviewer_ids(record))
            identity = record.get(identity_key)
            if not isinstance(identity, str) or not identity:
                raise TruthReviewError(f"truth record identity is missing: {name}")
            proposed = _blind(record)
            subject_id = f"{kind}:{identity}"
            subjects.append(
                {
                    "kind": kind,
                    "proposed_record": proposed,
                    "subject_id": subject_id,
                    "subject_sha256": _digest(proposed),
                }
            )
    subjects.sort(key=lambda item: str(item["subject_id"]))
    if len({item["subject_id"] for item in subjects}) != len(subjects):
        raise TruthReviewError("truth review subject identities must be unique")
    subjects_payload = b"".join(canonical(item) + b"\n" for item in subjects)
    manifest: dict[str, object] = {
        "schema_version": PACKET_SCHEMA,
        "source_commit": source_commit,
        "protocol_sha256": _digest_bytes(protocol),
        "corpus_lock_sha256": _digest_bytes(lock_bytes),
        "truth_files": truth_files,
        "sources": sources,
        "subject_count": len(subjects),
        "subject_counts": {
            kind: sum(item["kind"] == kind for item in subjects)
            for kind in sorted(_TRUTH_FILES)
        },
        "subjects_sha256": _digest_bytes(subjects_payload),
        "prohibited_reviewer_identity_sha256": sorted(
            _digest(item) for item in author_ids
        ),
        "system_output_included": False,
    }
    manifest["packet_id"] = "sha256:" + _digest(manifest)
    output_directory.mkdir(parents=True)
    (output_directory / "manifest.json").write_text(_pretty(manifest), encoding="utf-8")
    (output_directory / "subjects.jsonl").write_bytes(subjects_payload)
    (output_directory / "protocol.md").write_bytes(protocol)
    source_root = output_directory / "sources"
    source_root.mkdir()
    for source in sources:
        source_path = research_root / str(source["local_path"])
        shutil.copyfile(source_path, source_root / str(source["packet_path"]))
    template = {
        "schema_version": REVIEW_SCHEMA,
        "packet_id": manifest["packet_id"],
        "review_id": None,
        "reviewer_id": None,
        "reviewed_on": None,
        "source_material_reviewed": True,
        "system_output_consulted": False,
        "decisions": [
            {
                "conflicts": [],
                "proposed_correction": None,
                "rationale": None,
                "subject_id": item["subject_id"],
                "subject_sha256": item["subject_sha256"],
                "verdict": None,
            }
            for item in subjects
        ],
    }
    (output_directory / "review-template.json").write_text(
        _pretty(template), encoding="utf-8"
    )
    return manifest


def seal_truth_review(
    *, packet_directory: Path, draft: Mapping[str, object]
) -> dict[str, object]:
    """Validate a completed reviewer draft and bind its immutable identity."""

    manifest, subjects = _load_packet(packet_directory)
    value = dict(draft)
    value.pop("review_id", None)
    _validate_review_body(value, manifest=manifest, subjects=subjects)
    value["review_id"] = "sha256:" + _digest(value)
    return value


def seal_truth_adjudication(
    *,
    packet_directory: Path,
    reviews: Sequence[Mapping[str, object]],
    draft: Mapping[str, object],
) -> dict[str, object]:
    """Bind an adjudication to the exact complete independent review set."""

    manifest, subjects = _load_packet(packet_directory)
    admitted_reviews = tuple(
        _validate_sealed_review(item, manifest=manifest, subjects=subjects)
        for item in reviews
    )
    _validate_reviewers(admitted_reviews, manifest)
    value = dict(draft)
    value.pop("adjudication_id", None)
    _validate_adjudication_body(
        value,
        manifest=manifest,
        subjects=subjects,
        reviews=admitted_reviews,
    )
    value["adjudication_id"] = "sha256:" + _digest(value)
    return value


def admit_truth_reviews(
    *,
    packet_directory: Path,
    reviews: Sequence[Mapping[str, object]],
    adjudication: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Verify real reviewer separation and return a fail-closed admission report."""

    manifest, subjects = _load_packet(packet_directory)
    sealed = tuple(
        _validate_sealed_review(item, manifest=manifest, subjects=subjects)
        for item in reviews
    )
    _validate_reviewers(sealed, manifest)
    disagreement_ids, correction_ids = _review_issues(sealed, subjects)
    requires_adjudication = bool(disagreement_ids)
    sealed_adjudication: Mapping[str, object] | None = None
    if adjudication is not None:
        sealed_adjudication = _validate_sealed_adjudication(
            adjudication,
            manifest=manifest,
            subjects=subjects,
            reviews=sealed,
        )
    elif requires_adjudication:
        raise TruthReviewError(
            "review disagreement or requested change requires adjudication"
        )
    adjudicated = (
        {}
        if sealed_adjudication is None
        else {
            str(item["subject_id"]): str(item["verdict"])
            for item in _mapping_sequence(
                sealed_adjudication.get("decisions"), "adjudication decisions"
            )
        }
    )
    unanimous_approval = {
        subject_id
        for subject_id in subjects
        if all(
            _decision_by_id(review)[subject_id].get("verdict") == "approve"
            for review in sealed
        )
    }
    admitted_ids = {
        subject_id
        for subject_id in subjects
        if subject_id in unanimous_approval or adjudicated.get(subject_id) == "admit"
    }
    release_eligible = (
        admitted_ids == set(subjects) and not correction_ids and len(sealed) >= 2
    )
    report: dict[str, object] = {
        "schema_version": ADMISSION_SCHEMA,
        "packet_id": manifest["packet_id"],
        "source_commit": manifest["source_commit"],
        "review_ids": sorted(str(item["review_id"]) for item in sealed),
        "reviewer_ids": sorted(str(item["reviewer_id"]) for item in sealed),
        "adjudication_id": (
            None
            if sealed_adjudication is None
            else sealed_adjudication["adjudication_id"]
        ),
        "admitted_subject_count": len(admitted_ids),
        "required_subject_count": len(subjects),
        "disagreement_subject_ids": sorted(disagreement_ids),
        "correction_required_subject_ids": sorted(correction_ids),
        "release_eligible": release_eligible,
        "manual_signoff_verified": release_eligible,
        "system_output_consulted": False,
    }
    report["admission_id"] = "sha256:" + _digest(report)
    return report


def _source_manifest(
    lock: Mapping[str, object], research_root: Path
) -> list[dict[str, object]]:
    raw_sources = _mapping_sequence(lock.get("sources"), "corpus lock sources")
    result: list[dict[str, object]] = []
    for record in raw_sources:
        source_id = record.get("source_id")
        local_path = record.get("local_path")
        expected = record.get("sha256")
        if not all(isinstance(item, str) and item for item in (source_id, local_path)):
            raise TruthReviewError("corpus source identity or path is invalid")
        if not isinstance(expected, str) or _SHA256.fullmatch(expected) is None:
            raise TruthReviewError("corpus source digest is invalid")
        path = research_root / cast(str, local_path)
        payload = _regular_bytes(path, f"corpus source {source_id}")
        if _digest_bytes(payload) != expected:
            raise TruthReviewError(f"corpus source digest differs: {source_id}")
        result.append(
            {
                "local_path": local_path,
                "packet_path": f"{source_id}.xml",
                "sha256": expected,
                "source_id": source_id,
            }
        )
    result.sort(key=lambda item: str(item["source_id"]))
    return result


def _load_packet(
    directory: Path,
) -> tuple[Mapping[str, object], dict[str, Mapping[str, object]]]:
    manifest = _object(
        json.loads(_regular_bytes(directory / "manifest.json", "packet manifest")),
        "packet manifest",
    )
    if manifest.get("schema_version") != PACKET_SCHEMA:
        raise TruthReviewError("truth review packet schema is unsupported")
    packet_id = manifest.get("packet_id")
    identity_payload = {
        key: value for key, value in manifest.items() if key != "packet_id"
    }
    if packet_id != "sha256:" + _digest(identity_payload):
        raise TruthReviewError("truth review packet identity mismatch")
    raw_subjects = _regular_bytes(directory / "subjects.jsonl", "packet subjects")
    if _digest_bytes(raw_subjects) != manifest.get("subjects_sha256"):
        raise TruthReviewError("truth review subjects digest mismatch")
    subjects = _canonical_jsonl(raw_subjects, "packet subjects")
    by_id = {str(item.get("subject_id")): item for item in subjects}
    if len(by_id) != len(subjects) or len(by_id) != manifest.get("subject_count"):
        raise TruthReviewError("truth review packet subject population differs")
    for source in _mapping_sequence(manifest.get("sources"), "packet sources"):
        source_payload = _regular_bytes(
            directory / "sources" / str(source.get("packet_path")),
            "packet source",
        )
        if _digest_bytes(source_payload) != source.get("sha256"):
            raise TruthReviewError("truth review packet source digest mismatch")
    return manifest, by_id


def _validate_review_body(
    review: Mapping[str, object],
    *,
    manifest: Mapping[str, object],
    subjects: Mapping[str, Mapping[str, object]],
) -> None:
    reviewer_id = review.get("reviewer_id")
    if (
        review.get("schema_version") != REVIEW_SCHEMA
        or review.get("packet_id") != manifest.get("packet_id")
        or not isinstance(reviewer_id, str)
        or not reviewer_id.strip()
        or review.get("source_material_reviewed") is not True
        or review.get("system_output_consulted") is not False
    ):
        raise TruthReviewError("truth review policy or packet binding is invalid")
    _date(review.get("reviewed_on"), "review date")
    decisions = _mapping_sequence(review.get("decisions"), "review decisions")
    by_id = {str(item.get("subject_id")): item for item in decisions}
    if len(by_id) != len(decisions) or set(by_id) != set(subjects):
        raise TruthReviewError("truth review decisions must cover every packet subject")
    for subject_id, decision in by_id.items():
        if decision.get("subject_sha256") != subjects[subject_id].get("subject_sha256"):
            raise TruthReviewError("truth review decision subject digest mismatch")
        verdict = decision.get("verdict")
        rationale = decision.get("rationale")
        conflicts = decision.get("conflicts")
        correction = decision.get("proposed_correction")
        if (
            verdict not in _REVIEW_VERDICTS
            or not isinstance(rationale, str)
            or not rationale.strip()
            or not isinstance(conflicts, list)
            or any(not isinstance(item, str) or not item for item in conflicts)
        ):
            raise TruthReviewError("truth review decision is incomplete")
        if verdict == "approve" and (conflicts or correction is not None):
            raise TruthReviewError(
                "approving review cannot retain conflicts or correction"
            )
        if verdict == "changes-required" and not isinstance(correction, Mapping):
            raise TruthReviewError(
                "requested truth change requires a proposed correction"
            )
        if verdict == "reject" and correction is not None:
            raise TruthReviewError("rejected truth cannot carry an admitted correction")


def _validate_sealed_review(
    review: Mapping[str, object],
    *,
    manifest: Mapping[str, object],
    subjects: Mapping[str, Mapping[str, object]],
) -> Mapping[str, object]:
    value = dict(review)
    review_id = value.pop("review_id", None)
    _validate_review_body(value, manifest=manifest, subjects=subjects)
    if review_id != "sha256:" + _digest(value):
        raise TruthReviewError("truth review identity mismatch")
    value["review_id"] = review_id
    return value


def _validate_reviewers(
    reviews: Sequence[Mapping[str, object]], manifest: Mapping[str, object]
) -> None:
    if len(reviews) < 2:
        raise TruthReviewError(
            "release truth requires at least two independent reviewers"
        )
    reviewer_ids = [str(item["reviewer_id"]) for item in reviews]
    if len(set(reviewer_ids)) != len(reviewer_ids):
        raise TruthReviewError("truth reviewers must be distinct")
    prohibited = set(
        _strings(
            manifest.get("prohibited_reviewer_identity_sha256"),
            "prohibited reviewer hashes",
        )
    )
    if any(_digest(item) in prohibited for item in reviewer_ids):
        raise TruthReviewError(
            "truth author or prior reviewer cannot approve release truth"
        )


def _validate_adjudication_body(
    value: Mapping[str, object],
    *,
    manifest: Mapping[str, object],
    subjects: Mapping[str, Mapping[str, object]],
    reviews: Sequence[Mapping[str, object]],
) -> None:
    adjudicator_id = value.get("adjudicator_id")
    review_ids = _strings(value.get("review_ids"), "adjudication review IDs")
    if (
        value.get("schema_version") != ADJUDICATION_SCHEMA
        or value.get("packet_id") != manifest.get("packet_id")
        or set(review_ids) != {str(item["review_id"]) for item in reviews}
        or not isinstance(adjudicator_id, str)
        or not adjudicator_id.strip()
        or adjudicator_id in {str(item["reviewer_id"]) for item in reviews}
        or value.get("source_material_reviewed") is not True
        or value.get("system_output_consulted") is not False
    ):
        raise TruthReviewError("truth adjudication policy or review binding is invalid")
    prohibited = set(
        _strings(
            manifest.get("prohibited_reviewer_identity_sha256"),
            "prohibited reviewer hashes",
        )
    )
    if _digest(adjudicator_id) in prohibited:
        raise TruthReviewError("truth author or prior reviewer cannot adjudicate")
    _date(value.get("adjudicated_on"), "adjudication date")
    decisions = _mapping_sequence(value.get("decisions"), "adjudication decisions")
    by_id = {str(item.get("subject_id")): item for item in decisions}
    required, _ = _review_issues(reviews, subjects)
    if len(by_id) != len(decisions) or set(by_id) != required:
        raise TruthReviewError(
            "adjudication must cover the exact disagreement and change population"
        )
    for decision in decisions:
        if (
            decision.get("verdict") not in _ADJUDICATION_VERDICTS
            or not isinstance(decision.get("rationale"), str)
            or not str(decision.get("rationale")).strip()
            or not isinstance(decision.get("resolved_conflict_ids"), list)
        ):
            raise TruthReviewError("truth adjudication decision is incomplete")


def _validate_sealed_adjudication(
    value: Mapping[str, object],
    *,
    manifest: Mapping[str, object],
    subjects: Mapping[str, Mapping[str, object]],
    reviews: Sequence[Mapping[str, object]],
) -> Mapping[str, object]:
    item = dict(value)
    identity = item.pop("adjudication_id", None)
    _validate_adjudication_body(
        item, manifest=manifest, subjects=subjects, reviews=reviews
    )
    if identity != "sha256:" + _digest(item):
        raise TruthReviewError("truth adjudication identity mismatch")
    item["adjudication_id"] = identity
    return item


def _review_issues(
    reviews: Sequence[Mapping[str, object]],
    subjects: Mapping[str, Mapping[str, object]],
) -> tuple[set[str], set[str]]:
    disagreement: set[str] = set()
    corrections: set[str] = set()
    decisions = tuple(_decision_by_id(review) for review in reviews)
    for subject_id in subjects:
        values = tuple(item[subject_id] for item in decisions)
        verdicts = {str(item.get("verdict")) for item in values}
        conflicts = {
            conflict
            for item in values
            for conflict in cast(list[str], item["conflicts"])
        }
        if len(verdicts) > 1 or verdicts != {"approve"} or conflicts:
            disagreement.add(subject_id)
        if any(item.get("proposed_correction") is not None for item in values):
            corrections.add(subject_id)
    return disagreement, corrections


def _decision_by_id(review: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    return {
        str(item["subject_id"]): item
        for item in _mapping_sequence(review.get("decisions"), "review decisions")
    }


def _blind(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _blind(item)
            for key, item in value.items()
            if str(key) not in _PROVENANCE_KEYS
        }
    if isinstance(value, list):
        return [_blind(item) for item in value]
    return value


def _reviewer_ids(value: object) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"reviewer_id", "adjudicator_id"} and isinstance(item, str):
                result.add(item)
            else:
                result.update(_reviewer_ids(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_reviewer_ids(item))
    return result


def _canonical_jsonl(payload: bytes, label: str) -> list[Mapping[str, object]]:
    result: list[Mapping[str, object]] = []
    for number, line in enumerate(payload.splitlines(), 1):
        if not line:
            raise TruthReviewError(f"blank {label} row: {number}")
        try:
            value = _object(json.loads(line), label)
        except json.JSONDecodeError as error:
            raise TruthReviewError(f"invalid {label} row: {number}") from error
        if canonical(value) != line:
            raise TruthReviewError(f"non-canonical {label} row: {number}")
        result.append(value)
    if not result:
        raise TruthReviewError(f"{label} must not be empty")
    return result


def _regular_bytes(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise TruthReviewError(f"{label} is not a regular file: {path}")
    return path.read_bytes()


def _object(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TruthReviewError(f"{label} must be an object")
    return cast(Mapping[str, object], value)


def _mapping_sequence(value: object, label: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list) or any(
        not isinstance(item, Mapping) for item in value
    ):
        raise TruthReviewError(f"{label} must be a list of objects")
    return [cast(Mapping[str, object], item) for item in value]


def _strings(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise TruthReviewError(f"{label} must be a list of text identities")
    return cast(list[str], value)


def _date(value: object, label: str) -> None:
    if not isinstance(value, str):
        raise TruthReviewError(f"{label} is missing")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise TruthReviewError(f"{label} is invalid") from error


def _digest(value: object) -> str:
    return _digest_bytes(canonical(value))


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _pretty(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _read_json(path: Path, label: str) -> Mapping[str, object]:
    try:
        return _object(json.loads(_regular_bytes(path, label)), label)
    except json.JSONDecodeError as error:
        raise TruthReviewError(f"{label} is invalid JSON") from error


def main() -> None:
    """Create, seal, or admit a corpus truth review artifact."""

    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    packet = commands.add_parser("packet")
    packet.add_argument("--truth-root", type=Path, required=True)
    packet.add_argument("--corpus-lock", type=Path, required=True)
    packet.add_argument("--research-root", type=Path, required=True)
    packet.add_argument("--protocol", type=Path, required=True)
    packet.add_argument("--source-commit", required=True)
    packet.add_argument("--output-directory", type=Path, required=True)
    seal_review = commands.add_parser("seal-review")
    seal_review.add_argument("--packet", type=Path, required=True)
    seal_review.add_argument("--draft", type=Path, required=True)
    seal_adjudication = commands.add_parser("seal-adjudication")
    seal_adjudication.add_argument("--packet", type=Path, required=True)
    seal_adjudication.add_argument(
        "--review", type=Path, action="append", required=True
    )
    seal_adjudication.add_argument("--draft", type=Path, required=True)
    admit = commands.add_parser("admit")
    admit.add_argument("--packet", type=Path, required=True)
    admit.add_argument("--review", type=Path, action="append", required=True)
    admit.add_argument("--adjudication", type=Path)
    args = parser.parse_args()
    try:
        if args.operation == "packet":
            result = create_truth_review_packet(
                truth_root=args.truth_root,
                corpus_lock_path=args.corpus_lock,
                research_root=args.research_root,
                protocol_path=args.protocol,
                source_commit=args.source_commit,
                output_directory=args.output_directory,
            )
        elif args.operation == "seal-review":
            result = seal_truth_review(
                packet_directory=args.packet,
                draft=_read_json(args.draft, "review draft"),
            )
        elif args.operation == "seal-adjudication":
            result = seal_truth_adjudication(
                packet_directory=args.packet,
                reviews=[_read_json(path, "sealed review") for path in args.review],
                draft=_read_json(args.draft, "adjudication draft"),
            )
        else:
            result = admit_truth_reviews(
                packet_directory=args.packet,
                reviews=[_read_json(path, "sealed review") for path in args.review],
                adjudication=(
                    None
                    if args.adjudication is None
                    else _read_json(args.adjudication, "sealed adjudication")
                ),
            )
    except (OSError, TruthReviewError) as error:
        raise SystemExit(f"truth review failed: {error}") from error
    print(_pretty(result), end="")


if __name__ == "__main__":
    main()


__all__ = [
    "TruthReviewError",
    "admit_truth_reviews",
    "create_truth_review_packet",
    "main",
    "seal_truth_adjudication",
    "seal_truth_review",
]
