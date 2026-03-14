#!/usr/bin/env python3
"""Scope-aware pre-edit gate for Claude Code PreToolUse hooks.

Exit codes:
    0 — edit allowed (file is in scope of an open entry)
    2 — edit BLOCKED (no open entry covers this file)

Zero dependencies beyond the stdlib.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CL_PATH = Path("docs/change-log.json")


def load_cl() -> dict | None:
    """Load change-log data. Return None on any error."""
    if not CL_PATH.exists():
        return None
    try:
        return json.loads(CL_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_gate_policy(meta: dict) -> dict:
    """Read tunable gate_policy from _meta, with safe defaults."""
    defaults = {
        "scope_mode": "prefix",
        "require_scope": True,
        "auto_include_tests": True,
        "auto_include_docs": True,
    }
    policy = meta.get("gate_policy", {})
    return {k: policy.get(k, v) for k, v in defaults.items()}


def get_target_path(stdin_data: dict) -> str | None:
    """Extract the relative file path being edited from PreToolUse JSON."""
    tool_input = stdin_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return None

    cwd = stdin_data.get("cwd", "") or os.getcwd()
    if cwd and file_path.startswith(cwd):
        rel = file_path[len(cwd) :].lstrip("/")
        return rel
    return file_path


def path_in_scope(target: str, scope_entries: list[str]) -> bool:
    """Check whether target path is covered by any scope entry."""
    for entry in scope_entries:
        if not entry:
            continue
        if entry.endswith("/"):
            if target.startswith(entry):
                return True
            continue
        if target == entry:
            return True
    return False


def auto_scope_expansions(scope_entries: list[str], policy: dict) -> list[str]:
    """Add automatic scope expansions based on policy."""
    extra: list[str] = []
    if policy.get("auto_include_tests"):
        code_prefixes = ("src/", "scripts/", "frontend/")
        has_code = any(e.startswith(p) or e == p for e in scope_entries for p in code_prefixes)
        if has_code:
            extra.append("tests/")
    if policy.get("auto_include_docs"):
        extra.append("docs/")
    return extra


def check_scope(stdin_data: dict) -> tuple[bool, str]:
    """Main gate logic. Returns (allowed: bool, reason: str)."""
    data = load_cl()
    if data is None:
        return False, "docs/change-log.json not found or invalid"

    meta = data.get("_meta", {})
    policy = get_gate_policy(meta)
    items = data.get("items", [])

    open_entries = [i for i in items if i.get("resolved") is False]
    if not open_entries:
        return False, "No open change-log entries"

    target = get_target_path(stdin_data)
    if target is None:
        return False, "Could not determine target file from tool input."

    all_scope: list[str] = []
    for entry in open_entries:
        entry_scope = entry.get("scope", entry.get("files", []))
        if isinstance(entry_scope, list):
            all_scope.extend(entry_scope)

    auto = auto_scope_expansions(all_scope, policy)
    all_scope.extend(auto)

    seen: set[str] = set()
    unique_scope: list[str] = []
    for s in all_scope:
        if s and s not in seen:
            seen.add(s)
            unique_scope.append(s)

    if not unique_scope:
        if policy.get("require_scope"):
            return False, "Open CL entries exist but none declare a scope."
        return True, "No scope declared (permissive mode)"

    if path_in_scope(target, unique_scope):
        return True, f"{target} is in scope"

    return False, f"{target} is NOT in scope of any open CL entry."


def main() -> int:
    """Entry point. Exit 0 = allow, exit 2 = block."""
    try:
        stdin_text = sys.stdin.read()
        stdin_data = json.loads(stdin_text) if stdin_text.strip() else {}
    except (json.JSONDecodeError, OSError):
        stdin_data = {}

    allowed, reason = check_scope(stdin_data)

    if allowed:
        return 0

    print(f"🚫 EDIT BLOCKED — {reason}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
