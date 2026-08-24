# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed loopback-first server entrypoint for the Runtime v2 API."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import sys

_WORKING_ROOT_ENVIRONMENT_KEY = "BIJUX_CANON_RUNTIME_WORKING_ROOT"
_API_DEPENDENCIES = frozenset({"fastapi", "starlette", "uvicorn"})


@dataclass(frozen=True)
class ServerSettings:
    """Validated process settings passed to the HTTP server."""

    host: str
    port: int
    log_level: str
    access_log: bool


ServerRunner = Callable[[ServerSettings], None]


def _port(value: str) -> int:
    port = int(value)
    if not 1 <= port <= 65_535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Serve the local-first bijux-canon-runtime v2 HTTP API from one "
            "initialized workspace."
        )
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help=(
            "Runtime workspace root; relative paths resolve from the calling "
            "directory. Defaults to BIJUX_CANON_RUNTIME_WORKING_ROOT or the "
            "Runtime configuration default."
        ),
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default: loopback only).",
    )
    parser.add_argument("--port", type=_port, default=8000)
    parser.add_argument(
        "--log-level",
        choices=("critical", "error", "warning", "info", "debug", "trace"),
        default="info",
    )
    parser.add_argument(
        "--no-access-log",
        action="store_true",
        help="Disable one-line HTTP access records.",
    )
    return parser


def _run_server(settings: ServerSettings) -> None:
    try:
        import uvicorn
        from bijux_canon_runtime.api.v2.app import app
    except ModuleNotFoundError as exc:
        missing_dependency = (
            exc.name.split(".", maxsplit=1)[0] if exc.name is not None else None
        )
        if missing_dependency in _API_DEPENDENCIES:
            raise RuntimeError(
                "HTTP dependencies are unavailable; install "
                "bijux-canon-runtime[api]"
            ) from exc
        raise
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        access_log=settings.access_log,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: ServerRunner = _run_server,
) -> int:
    """Parse process settings and serve the installed Runtime v2 application."""
    arguments = _parser().parse_args(argv)
    if arguments.workspace is not None:
        workspace = arguments.workspace.expanduser().resolve()
        os.environ[_WORKING_ROOT_ENVIRONMENT_KEY] = str(workspace)
    settings = ServerSettings(
        host=arguments.host,
        port=arguments.port,
        log_level=arguments.log_level,
        access_log=not arguments.no_access_log,
    )
    try:
        runner(settings)
    except RuntimeError as exc:
        print(f"bijux-canon-runtime-server: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["ServerSettings", "main"]
