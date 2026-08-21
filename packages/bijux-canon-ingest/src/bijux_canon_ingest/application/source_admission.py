# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application entrypoints for source format and resource admission."""

from __future__ import annotations

from collections.abc import Iterable

from bijux_canon_ingest.domain.source_admission import (
    AdmissionBudgets,
    AdmissionResult,
)
from bijux_canon_ingest.domain.source_discovery import DiscoveredSource
from bijux_canon_ingest.infra.adapters.file_admission import admit_filesystem_source


def admit_source(
    source: DiscoveredSource,
    *,
    declared_media_type: str | None = None,
    budgets: AdmissionBudgets | None = None,
) -> AdmissionResult:
    """Admit or reject one discovered source before format parsing."""

    return admit_filesystem_source(
        source,
        declared_media_type=declared_media_type,
        budgets=budgets,
    )


def admit_sources(
    sources: Iterable[DiscoveredSource],
    *,
    budgets: AdmissionBudgets | None = None,
) -> tuple[AdmissionResult, ...]:
    """Apply one policy to sources in their caller-provided deterministic order."""

    policy = budgets if budgets is not None else AdmissionBudgets()
    return tuple(admit_source(source, budgets=policy) for source in sources)


__all__ = ["admit_source", "admit_sources"]
