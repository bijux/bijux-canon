# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Shared control flow for typed admission-limit failures."""

from __future__ import annotations

from bijux_canon_ingest.domain.source_admission import AdmissionIssueCode


class AdmissionFailure(Exception):
    """Internal short-circuit carrying one public rejection reason."""

    def __init__(self, code: AdmissionIssueCode, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def enforce_count(
    count: int,
    limit: int,
    code: AdmissionIssueCode,
    name: str,
) -> None:
    """Reject a measured resource count above its finite policy limit."""

    if count > limit:
        raise AdmissionFailure(code, f"source exceeds {name}={limit}")


__all__ = ["AdmissionFailure", "enforce_count"]
