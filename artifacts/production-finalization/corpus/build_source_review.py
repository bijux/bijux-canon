#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import ssl
import sys
import time
from typing import Any
import urllib.parse
import urllib.request


USER_AGENT = "bijux-canon-corpus-review/1.0 (https://github.com/bijux/bijux-canon)"
MAX_RESPONSE_BYTES = 12 * 1024 * 1024


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


class CitationMetadata(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        attributes = dict(attrs)
        name = attributes.get("name", "")
        content = attributes.get("content")
        if name.startswith("citation_") and content is not None:
            self.values.setdefault(name, []).append(html.unescape(content))


def fetch(
    url: str, *, method: str = "GET", accept: str = "*/*"
) -> tuple[bytes, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        method=method,
        headers={"Accept": accept, "User-Agent": USER_AGENT},
    )
    started = time.monotonic()
    with urllib.request.urlopen(
        request, timeout=45, context=ssl.create_default_context()
    ) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise RuntimeError(f"response exceeds {MAX_RESPONSE_BYTES} bytes: {url}")
        final = urllib.parse.urlsplit(response.geturl())
        record = {
            "request_url": url,
            "final_origin": f"{final.scheme}://{final.netloc}",
            "final_path": final.path,
            "status": response.status,
            "content_type": response.headers.get_content_type(),
            "content_length_header": response.headers.get("Content-Length"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "response_bytes": len(body),
            "response_sha256": sha256(body),
            "duration_seconds": round(time.monotonic() - started, 6),
        }
    if record["status"] != 200:
        raise RuntimeError(f"unexpected status {record['status']}: {url}")
    return body, record


def date_parts(value: dict[str, Any]) -> str:
    parts = value["date-parts"][0]
    return "-".join(
        f"{part:02d}" if index else str(part) for index, part in enumerate(parts)
    )


def author_names(authors: list[dict[str, Any]]) -> list[str]:
    return [
        " ".join(part for part in (author.get("given"), author.get("family")) if part)
        for author in authors
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--unit-root", type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve(strict=True)
    package = args.package.resolve(strict=True)
    matrix_path = package / "matrices/corpus-sources.jsonl"
    rows = [json.loads(line) for line in matrix_path.read_text().splitlines() if line]
    graph = json.loads((package.parent / "state/live-graph.json").read_text())
    units = {
        unit["matrix_key"]["source_id"]: unit
        for unit in graph["units"]
        if unit["task_id"] == "CORPUS-002"
    }
    if len(rows) != 8 or len(units) != len(rows):
        raise RuntimeError("CORPUS-002 requires exactly eight graph-backed matrix rows")

    policy_url = "https://journals.plos.org/plosone/s/licenses-and-copyright"
    policy_body, policy_transport = fetch(policy_url, accept="text/html")
    policy_text = policy_body.decode("utf-8")
    if "Creative Commons Attribution 4.0 International" not in policy_text:
        raise RuntimeError("PLOS policy does not state CC BY 4.0")

    nonexistent_doi = "10.1371/journal.pone.999999999999"
    negative_url = "https://api.plos.org/search?" + urllib.parse.urlencode(
        {"q": f'id:"{nonexistent_doi}"', "fl": "id", "wt": "json"}
    )
    negative_body, negative_transport = fetch(negative_url, accept="application/json")
    if json.loads(negative_body)["response"]["numFound"] != 0:
        raise RuntimeError("negative DOI control unexpectedly resolved")

    records: list[dict[str, Any]] = []
    for row in rows:
        doi = row["doi"]
        source_id = row["source_id"]
        journal_path = "plosbiology" if ".pbio." in doi else "plosone"
        quoted_doi = urllib.parse.quote(doi, safe="")
        canonical_url = (
            f"https://journals.plos.org/{journal_path}/article?id={quoted_doi}"
        )
        api_url = "https://api.plos.org/search?" + urllib.parse.urlencode(
            {
                "q": f'id:"{doi}"',
                "fl": "id,title,author_display,publication_date,journal,eissn",
                "wt": "json",
            }
        )
        crossref_url = f"https://api.crossref.org/works/{quoted_doi}"
        jats_url = f"https://journals.plos.org/{journal_path}/article/file?id={quoted_doi}&type=manuscript"
        pdf_url = f"https://journals.plos.org/{journal_path}/article/file?id={quoted_doi}&type=printable"

        api_body, api_transport = fetch(api_url, accept="application/json")
        api_document = json.loads(api_body)["response"]
        if api_document["numFound"] != 1:
            raise RuntimeError(f"PLOS API did not resolve exactly one record for {doi}")
        api_record = api_document["docs"][0]

        crossref_body, crossref_transport = fetch(
            crossref_url, accept="application/json"
        )
        crossref_message = json.loads(crossref_body)["message"]
        selected_crossref = {
            "DOI": crossref_message["DOI"],
            "URL": crossref_message["URL"],
            "author": crossref_message["author"],
            "container-title": crossref_message["container-title"],
            "issued": crossref_message["issued"],
            "license": crossref_message["license"],
            "publisher": crossref_message["publisher"],
            "title": crossref_message["title"],
            "type": crossref_message["type"],
        }

        article_body, article_transport = fetch(canonical_url, accept="text/html")
        article_text = article_body.decode("utf-8")
        metadata_parser = CitationMetadata()
        metadata_parser.feed(article_text)
        metadata = metadata_parser.values
        copyright_match = re.search(
            r"<strong>Copyright: </strong>(.*?)(?:</p>)", article_text, re.DOTALL
        )
        if copyright_match is None:
            raise RuntimeError(f"article copyright statement missing for {doi}")
        copyright_statement = html.unescape(
            re.sub(r"<[^>]+>", "", copyright_match.group(1))
        ).strip()

        _, jats_transport = fetch(
            jats_url, method="HEAD", accept="application/xml,text/xml"
        )
        _, pdf_transport = fetch(pdf_url, method="HEAD", accept="application/pdf")

        titles = [
            api_record["title"],
            selected_crossref["title"][0],
            metadata["citation_title"][0],
        ]
        if len({normalized(title) for title in titles}) != 1:
            raise RuntimeError(f"authoritative title disagreement for {doi}: {titles}")
        api_authors = api_record["author_display"]
        crossref_authors = author_names(selected_crossref["author"])
        page_authors = metadata["citation_author"]
        if [normalized(name) for name in api_authors] != [
            normalized(name) for name in page_authors
        ]:
            raise RuntimeError(f"PLOS author disagreement for {doi}")
        if [normalized(name) for name in crossref_authors] != [
            normalized(name) for name in page_authors
        ]:
            raise RuntimeError(f"Crossref author disagreement for {doi}")
        if (
            api_record["id"].casefold() != doi
            or selected_crossref["DOI"].casefold() != doi
        ):
            raise RuntimeError(f"DOI disagreement for {doi}")
        license_urls = {
            item["URL"].replace("http://", "https://", 1)
            for item in selected_crossref["license"]
        }
        if license_urls != {"https://creativecommons.org/licenses/by/4.0/"}:
            raise RuntimeError(
                f"unexpected article-specific license for {doi}: {license_urls}"
            )
        if "Creative Commons Attribution License" not in copyright_statement:
            raise RuntimeError(f"article copyright statement is not CC BY for {doi}")
        if jats_transport["content_type"] not in {"application/xml", "text/xml"}:
            raise RuntimeError(f"JATS endpoint MIME mismatch for {doi}")
        if pdf_transport["content_type"] != "application/pdf":
            raise RuntimeError(f"PDF endpoint MIME mismatch for {doi}")

        publication_date = api_record["publication_date"].removesuffix("T00:00:00Z")
        if publication_date != date_parts(selected_crossref["issued"]):
            raise RuntimeError(f"publication date disagreement for {doi}")
        citation = (
            f"{', '.join(page_authors)} ({publication_date[:4]}). "
            f"{titles[0]}. {metadata['citation_journal_title'][0]} "
            f"{metadata['citation_volume'][0]}({metadata['citation_issue'][0]}):"
            f"{metadata['citation_firstpage'][0]}. https://doi.org/{doi}"
        )
        core = {
            "source_id": source_id,
            "doi": doi,
            "title": titles[0],
            "authors": page_authors,
            "journal": metadata["citation_journal_title"][0],
            "publication_date": publication_date,
            "publication_year": int(publication_date[:4]),
            "publisher": selected_crossref["publisher"],
            "canonical_landing_page": canonical_url,
            "preferred_media": row["preferred_media"],
            "license": {
                "expression": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                "url": "https://creativecommons.org/licenses/by/4.0/",
                "article_copyright_statement": copyright_statement,
                "scope": "version-of-record article content; linked or separately credited third-party assets require their own review",
            },
            "attribution": citation,
            "access_terms": "public HTTPS access without authentication",
            "redistribution_terms": "copy, redistribute, adapt, and use commercially with attribution and indication of changes under CC BY 4.0",
            "retrieval_policy": {
                "admitted_media": ["jats"],
                "approved_request_origins": ["https://journals.plos.org"],
                "approved_redirect_origins": ["https://storage.googleapis.com"],
                "approved_redirect_path_prefix": "/plos-corpus-prod/",
                "maximum_response_bytes": MAX_RESPONSE_BYTES,
                "authentication_allowed": False,
                "redirect_requires_matching_doi_path": True,
                "immutable_identity_required": True,
                "supplementary_assets_require_separate_review": True,
            },
        }
        record_identity = sha256(canonical(core))
        record = {
            **core,
            "state": "license_reviewed",
            "disposition": "verified_complete",
            "record_identity_sha256": record_identity,
            "authoritative_evidence": {
                "plos_article": article_transport,
                "plos_search_api": api_transport,
                "plos_search_record_sha256": sha256(canonical(api_record)),
                "crossref_deposit": crossref_transport,
                "crossref_selected_record_sha256": sha256(canonical(selected_crossref)),
                "plos_license_policy": policy_transport,
                "plos_license_policy_url": policy_url,
            },
            "media": [
                {
                    "media_type": "text/html",
                    "role": "canonical_landing_page",
                    "transport": article_transport,
                },
                {
                    "media_type": "application/xml",
                    "role": "jats_manuscript",
                    "transport": jats_transport,
                },
                {
                    "media_type": "application/pdf",
                    "role": "printable_version",
                    "transport": pdf_transport,
                },
            ],
            "limitations": [
                "This review authorizes acquisition of the JATS version of record; it does not claim acquisition, parsing, truth annotation, admission, held-out use, or publication.",
                "Supplementary files and separately credited third-party assets are outside this unit decision until individually reviewed.",
            ],
        }
        records.append(record)

    corpus_core = [
        {
            "source_id": record["source_id"],
            "record_identity_sha256": record["record_identity_sha256"],
        }
        for record in records
    ]
    corpus_identity = sha256(canonical(corpus_core))
    unit_results = [
        {
            "unit_id": units[record["source_id"]]["unit_id"],
            "source_id": record["source_id"],
            "format_id": units[record["source_id"]]["matrix_key"].get("format_id"),
            "status": "passed",
            "disposition": "verified_complete",
            "record_identity_sha256": record["record_identity_sha256"],
        }
        for record in records
    ]
    source_commit = (
        __import__("subprocess")
        .check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True)
        .strip()
    )
    installed_audit_path = (
        repo
        / "artifacts/production-finalization/ingest/ingest-002/installed-audit-process-1.json"
    )
    installed_evidence_path = (
        repo / "artifacts/production-finalization/ingest/ingest-002.json"
    )
    installed_audit = json.loads(installed_audit_path.read_text())
    installed_evidence = json.loads(installed_evidence_path.read_text())
    result = {
        "schema_version": "bijux.canon.production_finalization.corpus_source_review.v1",
        "task_id": "CORPUS-002",
        "task_status": "in_progress",
        "source_commit": source_commit,
        "result": "passed",
        "disposition": "verified_complete",
        "required_rows": len(rows),
        "verified_rows": len(records),
        "unit_results": unit_results,
        "corpus_identity_sha256": corpus_identity,
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
        },
        "governing_identities": {
            "corpus_matrix_sha256": sha256(matrix_path.read_bytes()),
            "document_corpus_and_license_contract_sha256": sha256(
                (
                    package / "contracts/DOCUMENT_CORPUS_AND_LICENSE_CONTRACT.md"
                ).read_bytes()
            ),
            "evaluation_truth_contract_sha256": sha256(
                (package / "contracts/EVALUATION_TRUTH_CONTRACT.md").read_bytes()
            ),
            "root_pyproject_sha256": sha256((repo / "pyproject.toml").read_bytes()),
            "uv_lock_sha256": sha256((repo / "uv.lock").read_bytes()),
        },
        "verification": {
            "authoritative_sources": [
                "PLOS article landing pages",
                "PLOS Search API",
                "PLOS manuscript and printable media endpoints",
                "PLOS licenses and copyright policy",
                "Crossref DOI records deposited by Public Library of Science",
            ],
            "checks": [
                "DOI equality",
                "title equality across three records",
                "ordered author equality across three records",
                "publication-date equality",
                "article-specific CC BY statement",
                "article-specific Crossref CC BY 4.0 URL",
                "PLOS policy CC BY 4.0 statement",
                "JATS and PDF endpoint MIME",
                "bounded unauthenticated HTTPS retrieval",
                "negative DOI refusal",
            ],
            "negative_control": {
                "doi": nonexistent_doi,
                "expected_records": 0,
                "observed_records": 0,
                "transport": negative_transport,
            },
            "installed_surface": {
                "evidence_path": str(installed_evidence_path.relative_to(repo)),
                "evidence_sha256": sha256(installed_evidence_path.read_bytes()),
                "audit_path": str(installed_audit_path.relative_to(repo)),
                "audit_sha256": sha256(installed_audit_path.read_bytes()),
                "installed_version": installed_evidence["environment"][
                    "installed_version"
                ],
                "installed_python": installed_evidence["environment"][
                    "installed_python"
                ],
                "installed_module_origin": installed_evidence["environment"][
                    "installed_module_origin"
                ],
                "source_tree_imports": installed_evidence["environment"][
                    "source_tree_imports"
                ],
                "real_input_records": len(installed_audit["records"]),
                "real_input_audit_equal_across_processes": installed_evidence[
                    "real_input"
                ]["two_process_outputs_equal"],
            },
            "initial_failures": [
                {
                    "scope": "retained evidence builder formatting",
                    "reason": "The first Ruff format check reported that the ignored evidence builder would be reformatted; the builder was formatted without changing review semantics and all checks were rerun.",
                    "retained_output": "tool execution transcript",
                },
                {
                    "scope": "commit receipt path binding",
                    "reason": "The first evidence-anchor commit was empty, and immediate receipt-schema validation correctly rejected its empty staged_paths list before writing any receipt or event. The reproducible builder was then tracked inside the task's declared artifact write set and the unrecorded commit amended before evidence regeneration.",
                    "retained_output": "tool execution transcript",
                },
                {
                    "scope": "matrix unit evidence envelope",
                    "reason": "The first unit self-check correctly rejected the per-source evidence because it lacked the generic unit_results envelope required by the control plane. No unit receipt was written; the builder now emits exact unit, matrix-key, disposition, status, and record identities in both aggregate and per-source evidence.",
                    "retained_output": "tool execution transcript",
                },
            ],
        },
        "records": records,
        "limitations": [
            "No corpus bytes were admitted or published by this review.",
            "CORPUS-003 owns immutable acquisition; CORPUS-004 owns validated full-text JATS materialization.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )

    if args.unit_root is not None:
        for record in records:
            unit = units[record["source_id"]]
            unit_token = sha256(unit["unit_id"].encode())[:16]
            unit_path = args.unit_root / unit_token / "corpus-source-review.json"
            unit_path.parent.mkdir(parents=True, exist_ok=True)
            unit_evidence = {
                "schema_version": "bijux.canon.production_finalization.corpus_source_review_unit.v1",
                "task_id": "CORPUS-002",
                "unit_id": unit["unit_id"],
                "source_commit": source_commit,
                "row_sha256": unit["row_sha256"],
                "disposition": "verified_complete",
                "corpus_identity_sha256": corpus_identity,
                "record": record,
                "unit_results": [
                    result
                    for result in unit_results
                    if result["unit_id"] == unit["unit_id"]
                ],
            }
            unit_path.write_text(
                json.dumps(unit_evidence, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            )

    print(
        json.dumps(
            {
                "corpus_identity_sha256": corpus_identity,
                "output": str(args.output),
                "source_commit": source_commit,
                "verified_rows": len(records),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"source review failed: {error}", file=sys.stderr)
        raise
