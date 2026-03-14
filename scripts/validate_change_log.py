#!/usr/bin/env python3
"""Validate docs/change-log.json schema, scope, and traceability rules.

Pre-commit hook: ensures every change-log entry has required fields,
valid types/severity, scope declarations, and that resolved items include
full traceability (requirement_refs, test_refs, requirement_change, fixed).

Check IDs:
  VLID-1: JSON structure and _meta section present
  VLID-2: Required fields on every item
  VLID-3: Type and severity values are valid
  VLID-4: Scope is present and well-formed on open entries
  VLID-5: Resolved entries have full traceability metadata

Zero dependencies beyond the stdlib.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "id", "type", "severity", "resolved",
    "component", "summary", "details", "files", "created",
]
DEFAULT_TYPES = {"bug", "enhancement"}
DEFAULT_SEVERITIES = {"critical", "major", "minor", "cosmetic"}


def validate(path: Path) -> list[str]:
    """Return a list of error strings (empty = pass)."""
    if not path.exists():
        return [f"{path} not found"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON — {exc}"]

    if "_meta" not in data:
        return [f"{path}: missing _meta section"]
    if "items" not in data:
        return [f"{path}: missing items array"]

    meta = data["_meta"]
    valid_types = set(meta.get("types", DEFAULT_TYPES))
    valid_severities = set(meta.get("severity", DEFAULT_SEVERITIES))

    policy = meta.get("gate_policy", {})
    require_scope = policy.get("require_scope", True)

    errors: list[str] = []
    for item in data["items"]:
        item_id = item.get("id", "???")

        for field in REQUIRED_FIELDS:
            if field not in item:
                errors.append(f"{item_id}: missing required field '{field}'")

        if item.get("type") not in valid_types:
            errors.append(
                f"{item_id}: invalid type '{item.get('type')}' "
                f"(expected {valid_types})"
            )
        if item.get("severity") not in valid_severities:
            errors.append(
                f"{item_id}: invalid severity '{item.get('severity')}' "
                f"(expected {valid_severities})"
            )

        scope = item.get("scope")
        if scope is not None:
            if not isinstance(scope, list):
                errors.append(f"{item_id}: 'scope' must be an array")
            elif any(not isinstance(s, str) or not s.strip() for s in scope):
                errors.append(f"{item_id}: 'scope' entries must be non-empty strings")
        elif require_scope and item.get("resolved") is False:
            errors.append(
                f"{item_id}: open entry missing 'scope' "
                f"(gate_policy.require_scope=true)"
            )

        if "files" in item and not isinstance(item["files"], list):
            errors.append(f"{item_id}: 'files' must be an array")

        if item.get("resolved") is True:
            if "requirement_change" not in item:
                errors.append(
                    f"{item_id}: resolved=true but missing 'requirement_change'"
                )
            if "fixed" not in item:
                errors.append(
                    f"{item_id}: resolved=true but missing 'fixed' timestamp"
                )

            req_refs = item.get("requirement_refs")
            if not req_refs or not isinstance(req_refs, list) or len(req_refs) == 0:
                errors.append(
                    f"{item_id}: resolved=true but missing 'requirement_refs'"
                )

            test_refs = item.get("test_refs")
            if not test_refs or not isinstance(test_refs, list) or len(test_refs) == 0:
                errors.append(
                    f"{item_id}: resolved=true but missing 'test_refs'"
                )

    return errors


def main() -> int:
    """Entry point for pre-commit hook."""
    log_path = Path("docs/change-log.json")
    errors = validate(log_path)
    if errors:
        print(
            f"change-log validation failed ({len(errors)} error(s)):",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        return 1
    print("✓ docs/change-log.json is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
