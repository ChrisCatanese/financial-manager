#!/usr/bin/env python3
"""Create a new change-log entry with declared scope.

Usage:
    python3 scripts/cl_new.py --type bug --severity minor \
        --component "engine" \
        --summary "Fix bracket calculation" \
        --scope "src/financial_manager/engine/"

Zero dependencies beyond the stdlib.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CL_PATH = Path("docs/change-log.json")

VALID_TYPES = {"bug", "enhancement"}
VALID_SEVERITIES = {"critical", "major", "minor", "cosmetic"}


def load_cl() -> dict:
    """Load and return the change-log data."""
    if not CL_PATH.exists():
        print(f"✗ {CL_PATH} not found", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(CL_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"✗ {CL_PATH}: invalid JSON — {exc}", file=sys.stderr)
        sys.exit(1)


def next_id(data: dict) -> str:
    """Compute the next CL-NNNNN id."""
    meta = data.get("_meta", {})
    if "next_id" in meta:
        n = int(meta["next_id"])
    else:
        items = data.get("items", [])
        max_n = 0
        for item in items:
            item_id = item.get("id", "")
            if item_id.startswith("CL-"):
                try:
                    max_n = max(max_n, int(item_id.split("-")[1]))
                except (IndexError, ValueError):
                    pass
        n = max_n + 1
    return f"CL-{n:05d}"


def main() -> int:
    """Parse args and add a new change-log entry."""
    parser = argparse.ArgumentParser(description="Create a new change-log entry.")
    parser.add_argument("--type", required=True, choices=sorted(VALID_TYPES))
    parser.add_argument("--severity", required=True, choices=sorted(VALID_SEVERITIES))
    parser.add_argument("--component", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--scope", nargs="+", required=True)
    parser.add_argument("--details", default="")

    args = parser.parse_args()
    data = load_cl()
    entry_id = next_id(data)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entry = {
        "id": entry_id,
        "type": args.type,
        "severity": args.severity,
        "resolved": False,
        "component": args.component,
        "summary": args.summary,
        "details": args.details,
        "scope": args.scope,
        "files": [],
        "created": now,
    }

    data["items"].append(entry)
    meta = data.get("_meta", {})
    current_n = int(entry_id.split("-")[1])
    meta["next_id"] = current_n + 1
    data["_meta"] = meta

    CL_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"✓ Created {entry_id} — {args.type}/{args.severity}: {args.summary}")
    print(f"  Scope: {', '.join(args.scope)}")
    print(f"  When done, resolve with: python3 scripts/cl_resolve.py {entry_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
