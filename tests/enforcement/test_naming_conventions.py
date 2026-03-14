"""Naming convention enforcement.

Criteria enforced:
  NAME-01: All .py files in src/ use snake_case
  NAME-02: Test files follow test_*.py convention
  NAME-03: Python classes use PascalCase
  NAME-04: Module-level constants use UPPER_SNAKE_CASE

Run with:  pytest tests/enforcement/test_naming_conventions.py -v
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from .conftest import EXCLUDED_DIRS, PACKAGE_DIR, ROOT

TESTS_DIR = ROOT / "tests"

SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
PASCAL_CASE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
UPPER_SNAKE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _python_files_in(directory: Path) -> list[Path]:
    """List all .py files in a directory excluding caches."""
    results = []
    if not directory.exists():
        return results
    for p in directory.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in p.parts):
            continue
        results.append(p)
    return sorted(results)


class TestPythonFileNaming:
    """NAME-01: All .py files in src/ must be snake_case."""

    def test_all_python_files_snake_case(self):
        """Source files must use snake_case naming."""
        violations: list[str] = []
        for fpath in _python_files_in(PACKAGE_DIR):
            stem = fpath.stem
            if stem.startswith("__") and stem.endswith("__"):
                continue
            if not SNAKE_CASE_RE.match(stem):
                violations.append(str(fpath.relative_to(ROOT)))
        assert not violations, "NAME-01: Non-snake_case Python files:\n" + "\n".join(f"  {v}" for v in violations)


class TestTestFileNaming:
    """NAME-02: Test files must follow test_*.py convention."""

    def test_test_files_follow_convention(self):
        """All test files must be named test_*.py."""
        violations: list[str] = []
        for fpath in TESTS_DIR.rglob("*.py"):
            if "__pycache__" in str(fpath):
                continue
            stem = fpath.stem
            if stem.startswith("__"):
                continue
            if stem == "conftest":
                continue
            if not stem.startswith("test_"):
                violations.append(str(fpath.relative_to(ROOT)))
        assert not violations, "NAME-02: Test files not following test_*.py convention:\n" + "\n".join(
            f"  {v}" for v in violations
        )


class TestClassNaming:
    """NAME-03: Python classes should use PascalCase naming."""

    _EXEMPT = re.compile(r"^(type_|_)")

    def test_src_classes_use_pascal_case(self):
        """All classes in src/ must use PascalCase."""
        violations: list[str] = []
        for fpath in _python_files_in(PACKAGE_DIR):
            try:
                tree = ast.parse(fpath.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    name = node.name
                    if self._EXEMPT.match(name):
                        continue
                    if not PASCAL_CASE_RE.match(name):
                        violations.append(f"  {fpath.relative_to(ROOT)}:{node.lineno}: " f"class {name}")
        assert not violations, "NAME-03: Classes not using PascalCase:\n" + "\n".join(violations)


class TestConstantNaming:
    """NAME-04: Module-level constants should use UPPER_SNAKE_CASE."""

    _EXEMPT = frozenset(
        {
            "__all__",
            "__version__",
            "__author__",
            "logger",
            "app",
            "log",
        }
    )

    def test_src_constants_naming(self):
        """All-caps module-level names must use UPPER_SNAKE_CASE."""
        violations: list[str] = []
        for fpath in _python_files_in(PACKAGE_DIR):
            try:
                tree = ast.parse(fpath.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            name = target.id
                            if name in self._EXEMPT or name.startswith("_"):
                                continue
                            if name.isupper() and not UPPER_SNAKE_RE.match(name):
                                violations.append(f"  {fpath.relative_to(ROOT)}:{node.lineno}: " f"{name}")
        assert not violations, "NAME-04: Constants not using UPPER_SNAKE_CASE:\n" + "\n".join(violations)
