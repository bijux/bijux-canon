# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Safe node and text accounting for markup and UTF-8 text sources."""

from __future__ import annotations

from html.parser import HTMLParser
import re
from urllib.parse import urlsplit
from xml.parsers import expat

from bijux_canon_ingest.domain.source_admission import AdmissionBudgets
from bijux_canon_ingest.infra.admission.limits import (
    AdmissionFailure,
    enforce_count,
)


class _HTMLCounter(HTMLParser):
    def __init__(self, budgets: AdmissionBudgets) -> None:
        super().__init__(convert_charrefs=True)
        self._budgets = budgets
        self.node_count = 0
        self.text_bytes = 0

    def _node(self) -> None:
        self.node_count += 1
        enforce_count(
            self.node_count,
            self._budgets.max_nodes,
            "node_budget_exceeded",
            "max_nodes",
        )

    def _text(self, size: int) -> None:
        self.text_bytes += size
        enforce_count(
            self.text_bytes,
            self._budgets.max_text_bytes,
            "text_budget_exceeded",
            "max_text_bytes",
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del tag, attrs
        self._node()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del tag, attrs
        self._node()

    def handle_data(self, data: str) -> None:
        self._text(len(data.encode("utf-8")))

    def handle_entityref(self, name: str) -> None:
        del name
        self._text(1)

    def handle_charref(self, name: str) -> None:
        del name
        self._text(1)


def inspect_html(content: bytes, budgets: AdmissionBudgets) -> tuple[int, int]:
    """Count bounded HTML nodes and text without semantic extraction."""

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise AdmissionFailure(
            "malformed_input", "HTML input is not valid UTF-8"
        ) from error
    lowered = text.casefold()
    if "<!entity" in lowered or re.search(r"<!doctype[^>]*\[", lowered):
        raise AdmissionFailure(
            "unsafe_markup", "HTML input contains an entity-bearing declaration"
        )
    counter = _HTMLCounter(budgets)
    try:
        counter.feed(text)
        counter.close()
    except AdmissionFailure:
        raise
    except Exception as error:
        raise AdmissionFailure("malformed_input", "HTML tokenization failed") from error
    return counter.node_count, counter.text_bytes


def inspect_xml(
    content: bytes,
    budgets: AdmissionBudgets,
) -> tuple[str, int, int]:
    """Count bounded XML nodes and text without resolving external resources."""

    node_count = 0
    text_bytes = 0
    root_name: str | None = None
    parser = expat.ParserCreate(namespace_separator="}")

    def start_element(name: str, attributes: dict[str, str]) -> None:
        nonlocal node_count, root_name
        del attributes
        node_count += 1
        enforce_count(
            node_count,
            budgets.max_nodes,
            "node_budget_exceeded",
            "max_nodes",
        )
        if root_name is None:
            root_name = name.rsplit("}", 1)[-1]

    def character_data(value: str) -> None:
        nonlocal text_bytes
        text_bytes += len(value.encode("utf-8"))
        enforce_count(
            text_bytes,
            budgets.max_text_bytes,
            "text_budget_exceeded",
            "max_text_bytes",
        )

    def inspect_doctype(
        name: str,
        system_id: str | None,
        public_id: str | None,
        has_internal_subset: int,
    ) -> None:
        if has_internal_subset:
            raise AdmissionFailure(
                "unsafe_markup", "XML internal document type subsets are forbidden"
            )
        if name != "article" or system_id is None:
            raise AdmissionFailure(
                "unsafe_markup", "XML document type is not an approved JATS declaration"
            )
        parsed = urlsplit(system_id)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"dtd.nlm.nih.gov", "jats.nlm.nih.gov"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or not parsed.path.casefold().endswith(".dtd")
        ):
            raise AdmissionFailure(
                "unsafe_markup",
                "XML document type does not reference an approved JATS DTD",
            )
        if public_id is not None and not public_id.startswith("-//NLM//DTD "):
            raise AdmissionFailure(
                "unsafe_markup", "XML document type has an unapproved public identifier"
            )

    def reject_entity(*arguments: object) -> None:
        del arguments
        raise AdmissionFailure("unsafe_markup", "XML entity declarations are forbidden")

    def reject_external_entity(*arguments: object) -> int:
        del arguments
        raise AdmissionFailure("unsafe_markup", "XML external entities are forbidden")

    parser.StartElementHandler = start_element
    parser.CharacterDataHandler = character_data
    parser.StartDoctypeDeclHandler = inspect_doctype
    parser.EntityDeclHandler = reject_entity
    parser.ExternalEntityRefHandler = reject_external_entity
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    try:
        parser.Parse(content, True)
    except AdmissionFailure:
        raise
    except expat.ExpatError as error:
        raise AdmissionFailure("malformed_input", "XML input is malformed") from error
    if root_name is None:
        raise AdmissionFailure("malformed_input", "XML input has no root element")
    return root_name, node_count, text_bytes


def inspect_text(content: bytes, budgets: AdmissionBudgets) -> int:
    """Validate UTF-8 and enforce the normalized text-byte budget."""

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise AdmissionFailure(
            "malformed_input", "text input is not valid UTF-8"
        ) from error
    text_bytes = len(text.encode("utf-8"))
    enforce_count(
        text_bytes,
        budgets.max_text_bytes,
        "text_budget_exceeded",
        "max_text_bytes",
    )
    return text_bytes


__all__ = ["inspect_html", "inspect_text", "inspect_xml"]
