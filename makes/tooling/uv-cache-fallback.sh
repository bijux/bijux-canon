#!/bin/sh

set -u

uv "$@"
online_status=$?
if [ "$online_status" -eq 0 ]; then
    exit 0
fi

if [ "${1:-}" != "pip" ] || [ "${2:-}" != "install" ]; then
    exit "$online_status"
fi

echo "→ uv online install failed; retrying from the local cache" >&2
UV_OFFLINE=1 uv "$@"
