# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Conservative, reproducible projections from exact evidence into concise claims."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+", flags=re.UNICODE)
_CONTRAST_BOUNDARY = re.compile(r";|,\s+(?:but|whereas|while)\s+", flags=re.IGNORECASE)
_PAIRED_RESULT = re.compile(
    r"^(?:Finally,\s+)?Our results confirm that (?P<confirmed>.+?) "
    r"and indicate that (?P<indicated>.+?)[.]?$",
    flags=re.IGNORECASE,
)
_ASSERTED_RESULT = re.compile(
    r"^(?:Finally,\s+)?(?:Our|The) results (?:also )?"
    r"(?:confirm|show) that (?P<claim>.+?)[.]?$",
    flags=re.IGNORECASE,
)
_AUTHORED_RESULT = re.compile(
    r"^(?:(?:Here|Lastly),?\s+)?we "
    r"(?:conclude|demonstrate|found|have shown|show) that (?P<claim>.+?)[.]?$",
    flags=re.IGNORECASE,
)
_STUDY_RESULT = re.compile(
    r"^(?:However,\s+)?(?:this|the) study shows that (?P<claim>.+?)[.]?$",
    flags=re.IGNORECASE,
)
_INDICATED_RESULT = re.compile(
    r"^(?:Our|The) results (?:also )?indicate that (?P<claim>.+?)[.]?$",
    flags=re.IGNORECASE,
)
_SAFE_MODALITY = re.compile(
    r"\b(?:at least|can|could|may|might|up to)\b", flags=re.IGNORECASE
)
_LABEL = re.compile(
    r"\((?P<label>(?:area|part|portion|region)\s+[A-Z0-9]+)\)",
    flags=re.IGNORECASE,
)


class EvidenceProjectionMethod(StrEnum):
    """Closed set of transformations accepted by deterministic verification."""

    exact_clause = "exact_clause"
    attribution_removed = "attribution_removed"
    labeled_definition = "labeled_definition"


@dataclass(frozen=True, slots=True)
class EvidenceProjection:
    """One concise statement reproducibly derived from an exact source clause."""

    statement: str
    method: EvidenceProjectionMethod


def project_evidence_clause(text: str) -> tuple[EvidenceProjection, ...]:
    """Return only meaning-preserving projections plus the exact-clause fallback."""

    clause = " ".join(text.split()).strip()
    if not clause:
        return ()
    projected: list[EvidenceProjection] = []
    paired = _PAIRED_RESULT.fullmatch(clause)
    if paired is not None:
        projected.append(
            EvidenceProjection(
                _sentence(paired.group("confirmed")),
                EvidenceProjectionMethod.attribution_removed,
            )
        )
        indicated = paired.group("indicated")
        if _SAFE_MODALITY.search(indicated):
            projected.append(
                EvidenceProjection(
                    _sentence(indicated),
                    EvidenceProjectionMethod.attribution_removed,
                )
            )
    else:
        asserted = _ASSERTED_RESULT.fullmatch(clause)
        authored = _AUTHORED_RESULT.fullmatch(clause)
        study_result = _STUDY_RESULT.fullmatch(clause)
        indicated = _INDICATED_RESULT.fullmatch(clause)
        if asserted is not None:
            projected.append(
                EvidenceProjection(
                    _sentence(asserted.group("claim")),
                    EvidenceProjectionMethod.attribution_removed,
                )
            )
        elif authored is not None:
            projected.append(
                EvidenceProjection(
                    _sentence(authored.group("claim")),
                    EvidenceProjectionMethod.attribution_removed,
                )
            )
        elif study_result is not None:
            projected.append(
                EvidenceProjection(
                    _sentence(study_result.group("claim")),
                    EvidenceProjectionMethod.attribution_removed,
                )
            )
        elif indicated is not None and _SAFE_MODALITY.search(indicated.group("claim")):
            projected.append(
                EvidenceProjection(
                    _sentence(indicated.group("claim")),
                    EvidenceProjectionMethod.attribution_removed,
                )
            )
    projected.extend(_labeled_definitions(clause))
    projected.append(EvidenceProjection(clause, EvidenceProjectionMethod.exact_clause))
    unique: dict[str, EvidenceProjection] = {}
    for item in projected:
        unique.setdefault(item.statement, item)
    return tuple(unique.values())


def project_evidence_text(text: str) -> tuple[EvidenceProjection, ...]:
    """Project every exact sentence in one immutable citation payload."""

    normalized = " ".join(text.split()).strip()
    if not normalized:
        return ()
    return tuple(
        projection
        for sentence in _SENTENCE_BOUNDARY.split(normalized)
        for clause in _CONTRAST_BOUNDARY.split(sentence)
        for projection in project_evidence_clause(clause)
    )


def _labeled_definitions(text: str) -> tuple[EvidenceProjection, ...]:
    matches = tuple(_LABEL.finditer(text))
    if len(matches) < 2:
        return ()
    definitions = []
    prior_end = 0
    for match in matches:
        description = text[prior_end : match.start()].strip(" ,:;")
        if prior_end == 0 and ":" in description:
            description = description.rsplit(":", maxsplit=1)[1].strip()
        description = re.sub(r"^(?:and|or)\s+", "", description, flags=re.IGNORECASE)
        if description:
            label_kind, label_identifier = match.group("label").rsplit(" ", maxsplit=1)
            definitions.append(
                EvidenceProjection(
                    f"{label_kind.capitalize()} {label_identifier.upper()} denotes {description}.",
                    EvidenceProjectionMethod.labeled_definition,
                )
            )
        prior_end = match.end()
    return tuple(definitions)


def _sentence(value: str) -> str:
    statement = value.strip(" ,;")
    if statement and statement[0].isalpha():
        statement = statement[0].upper() + statement[1:]
    if statement and statement[-1] not in ".!?":
        statement += "."
    return statement


__all__ = [
    "EvidenceProjection",
    "EvidenceProjectionMethod",
    "project_evidence_clause",
    "project_evidence_text",
]
