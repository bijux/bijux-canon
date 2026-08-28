# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Operator commands for the authoritative Runtime workspace."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import TextIO

from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)
from bijux_canon_runtime.application.workspace_initialization import (
    WorkspaceInitializationError,
    initialize_runtime_workspace,
)
from bijux_canon_runtime.core.errors import ConfigurationError

EXIT_INITIALIZATION_REFUSED = 2


def initialize_workspace(args: argparse.Namespace) -> int:
    """Initialize one workspace and emit a stable operator result."""
    try:
        configuration = resolve_runtime_configuration(
            environment=os.environ,
            explicit={
                "embedding_model_path": (
                    None
                    if args.model is None
                    else Path(args.model).expanduser().resolve()
                ),
                "working_root": args.workspace,
            },
        )
        result = initialize_runtime_workspace(configuration)
    except WorkspaceInitializationError as exc:
        payload = {
            "code": exc.code.value,
            "detail": exc.detail,
            "remediation": exc.remediation,
            "schema_version": "bijux.runtime.workspace-initialization-error.v1",
            "status": "refused",
        }
        if args.json:
            _write_json(payload, file=sys.stderr)
        else:
            print(
                f"Workspace initialization refused ({exc.code.value}): {exc.detail}",
                file=sys.stderr,
            )
            print(f"Next step: {exc.remediation}", file=sys.stderr)
        return EXIT_INITIALIZATION_REFUSED
    except ConfigurationError as exc:
        payload = {
            "code": "invalid_configuration",
            "detail": str(exc),
            "remediation": "correct the reported Runtime configuration and retry",
            "schema_version": "bijux.runtime.workspace-initialization-error.v1",
            "status": "refused",
        }
        if args.json:
            _write_json(payload, file=sys.stderr)
        else:
            print(
                f"Workspace initialization refused (invalid_configuration): {exc}",
                file=sys.stderr,
            )
            print(f"Next step: {payload['remediation']}", file=sys.stderr)
        return EXIT_INITIALIZATION_REFUSED
    if args.json:
        _write_json(result.record())
    else:
        print(f"Workspace {result.status.value}: {result.workspace_root}")
        print(f"Workspace ID: {result.workspace_id}")
        print(
            "Model lock: "
            + (result.model_lock_artifact_id if args.model is not None else "none")
        )
        if result.applied_migration_ids:
            print("Applied migrations: " + ", ".join(result.applied_migration_ids))
        if result.rollback_backup_path is not None:
            print(f"Rollback backup: {result.rollback_backup_path}")
    return 0


def _write_json(value: object, *, file: TextIO | None = None) -> None:
    destination = sys.stdout if file is None else file
    print(
        json.dumps(value, sort_keys=True, separators=(",", ":")),
        file=destination,
    )


__all__ = ["EXIT_INITIALIZATION_REFUSED", "initialize_workspace"]
