#!/usr/bin/env python3
"""VDI 2230 core bolt verification CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.bolt.calculator import InputError, calculate_vdi2230_core, load_input_json


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VDI 2230 core bolt verification tool")
    parser.add_argument("--input", required=True, help="Path to input JSON")
    parser.add_argument("--output", help="Optional path to save output JSON")
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON pretty indent (default: 2, use 0 for compact)",
    )
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    try:
        data = load_input_json(Path(args.input))
        result = calculate_vdi2230_core(data)
    except InputError as exc:
        print(f"[INPUT ERROR] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover
        print(f"[UNEXPECTED ERROR] {exc}", file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=max(args.indent, 0))

    print(json.dumps(result, ensure_ascii=False, indent=max(args.indent, 0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
