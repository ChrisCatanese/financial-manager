#!/usr/bin/env python3
"""Resolve a change-log entry (one-way transition).

Usage:
    python3 scripts/cl_resolve.py CL-00001 \
        --requirement-refs "TR-001" "FR-001" \
        --test-refs "tests/test_calculator.py::test_basic" \
        --requirement-change "Implemented progressive bracket calculation" \
        --files "src/financial_manager/engine/calculator.py"

Zero dependencies beyond the stdlib.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CL_PATH = Path("docs/change-log.json")


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


def main() -> int:
    """Parse args and resolve a change-log entry."""
    parser = argparse.ArgumentParser(description="Resolve a change-log entry.")
    parser.add_argument("entry_id")
    parser.add_argument("--requirement-refs", nargs="+", required=True)
    parser.add_argument("--test-refs", nargs="+", required=True)
    parser.add_argument("--requirement-change", required=True)
    parser.add_argument("--files", nargs="+", default=None)
    parser.add_argument("--scope-add", nargs="*", default=[])

    args = parser.parse_args()
    data = load_cl()
    items = data.get("items", [])

    target = None
    for item in items:
        if item.get("id") == args.entry_id:
            target = item
            break

    if target is None:
        print(f"✗ Entry {args.entry_id} not found", file=sys.stderr)
        return 1

    if target.get("resolved") is True:
        print(
            f"✗ Entry {args.entry_id} is already resolved (immutable).",
            file=sys.stderr,
        )
        return 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    target["resolved"] = True
    target["requirement_refs"] = args.requirement_refs
    target["test_refs"] = args.test_refs
    target["requirement_change"] = args.requirement_change
    target["fixed"] = now

    if args.files:
        target["files"] = args.files
    elif not target.get("files"):
        scope = target.get("scope", [])
        target["files"] = [s for s in scope if not s.endswith("/")]

    if args.scope_add:
        existing_scope = target.get("scope", [])
        for s in args.scope_add:
            if s not in existing_scope:
                existing_scope.append(s)
        target["scope"] = existing_scope

    CL_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"✓ Resolved {args.entry_id}")
    print(f"  requirement_refs: {args.requirement_refs}")
    print(f"  test_refs: {args.test_refs}")
    print(f"  fixed: {now}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
