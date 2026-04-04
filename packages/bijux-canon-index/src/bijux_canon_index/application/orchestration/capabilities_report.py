# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from typing import Any

from bijux_canon_index.core.execution_mode import ExecutionMode
from bijux_canon_index.infra.adapters.vectorstore_registry import VECTOR_STORES
from bijux_canon_index.infra.embeddings.registry import EMBEDDING_PROVIDERS
from bijux_canon_index.infra.runners.registry import RUNNERS


def build_capabilities_response(
    *,
    backend_name: str,
    caps: object | None,
    supports_ann: bool,
    default_runner: str | None,
    nd_health: dict[str, object],
    nd_notes: tuple[str, ...],
) -> dict[str, Any]:
    ann_status = "experimental" if supports_ann else "unavailable"
    execution_modes = [mode.value for mode in ExecutionMode]
    response: dict[str, Any] = {
        "backend": backend_name,
        "contracts": [],
        "deterministic_query": None,
        "supports_ann": supports_ann,
        "replayable": None,
        "metrics": [],
        "max_vector_size": None,
        "isolation_level": None,
        "execution_modes": execution_modes,
        "ann_status": ann_status,
        "nd": {
            "default_runner": default_runner,
            "health": nd_health,
            "notes": nd_notes,
        },
        "storage_backends": build_storage_backends(),
        "vector_stores": build_vector_store_reports(),
        "plugins": build_plugin_reports(),
    }
    if caps is None:
        return response
    response.update(
        {
            "contracts": sorted(
                c.value if hasattr(c, "value") else str(c)
                for c in (getattr(caps, "contracts", None) or [])
            ),
            "deterministic_query": getattr(caps, "deterministic_query", None),
            "replayable": getattr(caps, "replayable", None),
            "metrics": sorted(getattr(caps, "metrics", None) or []),
            "max_vector_size": getattr(caps, "max_vector_size", None),
            "isolation_level": getattr(caps, "isolation_level", None),
        }
    )
    return response


def build_storage_backends() -> list[dict[str, str]]:
    return [
        {
            "name": "memory",
            "status": "stable",
            "persistence": "ephemeral",
        },
        {
            "name": "sqlite",
            "status": "stable",
            "persistence": "local",
        },
        {
            "name": "hnsw",
            "status": "experimental",
            "persistence": "local",
        },
        {
            "name": "pgvector",
            "status": "experimental_excluded",
            "persistence": "external",
            "notes": "excluded from v1 freeze",
        },
    ]


def build_vector_store_reports() -> list[dict[str, object]]:
    return [
        {
            "name": desc.name,
            "available": desc.available,
            "supports_exact": desc.supports_exact,
            "supports_ann": desc.supports_ann,
            "delete_supported": desc.delete_supported,
            "filtering_supported": desc.filtering_supported,
            "deterministic_exact": desc.deterministic_exact,
            "experimental": desc.experimental,
            "consistency": desc.consistency,
            "version": desc.version,
            "notes": desc.notes,
        }
        for desc in VECTOR_STORES.descriptors()
    ]


def build_plugin_reports() -> dict[str, list[dict[str, object]]]:
    return {
        "vectorstores": VECTOR_STORES.plugin_reports(),
        "embeddings": EMBEDDING_PROVIDERS.plugin_reports(),
        "runners": RUNNERS.plugin_reports(),
    }


__all__ = ["build_capabilities_response"]
