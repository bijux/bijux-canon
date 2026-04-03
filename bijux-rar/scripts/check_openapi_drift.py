# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_canonical(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated", required=True)
    ap.add_argument("--pinned", required=True)
    ap.add_argument("--pin", action="store_true")
    args = ap.parse_args()

    generated = Path(args.generated)
    pinned = Path(args.pinned)

    gen_obj = load_json(generated)
    pin_obj = load_json(pinned) if pinned.exists() else None

    gen_txt = dump_canonical(gen_obj)
    pin_txt = dump_canonical(pin_obj) if pin_obj is not None else None

    if args.pin:
        pinned.parent.mkdir(parents=True, exist_ok=True)
        pinned.write_text(gen_txt, encoding="utf-8")
        return

    if pin_obj is None:
        raise SystemExit(
            f"Pinned OpenAPI schema missing: {pinned}. Run `make api_pin` intentionally."
        )

    if gen_txt != pin_txt:
        raise SystemExit(
            "API drift detected.\n"
            f"- Generated: {generated}\n"
            f"- Pinned:    {pinned}\n"
            "If this is intentional, run `make api_pin`."
        )


if __name__ == "__main__":
    main()
