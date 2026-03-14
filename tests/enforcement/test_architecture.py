"""Architecture enforcement — structural boundaries and import hygiene.

Criteria enforced:
  ARCH-01: src/ packages have __init__.py
  ARCH-02: No circular imports in src/
  ARCH-03: No deep relative imports
  ARCH-04: scripts/ does not import from test modules

Run with:  pytest tests/enforcement/test_architecture.py -v
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from .conftest import EXCLUDED_DIRS, PACKAGE_DIR, ROOT, SCRIPTS_DIR


def _python_files_in(directory: Path) -> list[Path]:
    """All .py files excluding __pycache__ and .venv."""
    results = []
    if not directory.exists():
        return results
    for p in directory.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in p.parts):
            continue
        results.append(p)
    return sorted(results)


def _extract_imports(filepath: Path) -> list[str]:
    """Extract all import module names from a Python file using AST."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


class TestPackageInitFiles:
    """ARCH-01: Python package directories under src/ must have __init__.py."""

    def test_src_packages_have_init(self):
        """Every directory in src/ with .py files must have __init__.py."""
        if not PACKAGE_DIR.exists():
            pytest.skip("src/ not found")
        missing: list[str] = []
        for subdir in PACKAGE_DIR.rglob("*"):
            if not subdir.is_dir():
                continue
            if any(part in EXCLUDED_DIRS for part in subdir.parts):
                continue
            if subdir.name.startswith((".", "__")):
                continue
            py_files = list(subdir.glob("*.py"))
            if py_files and not (subdir / "__init__.py").exists():
                missing.append(str(subdir.relative_to(ROOT)))
        assert not missing, "ARCH-01: Package directories missing __init__.py:\n" + "\n".join(f"  {m}" for m in missing)


class TestNoCircularImports:
    """ARCH-02: No circular import chains among src/ modules."""

    def test_no_circular_deps(self):
        """Build import graph for src/ and check for cycles via DFS."""
        src_files = _python_files_in(PACKAGE_DIR)
        if not src_files:
            pytest.skip("No source files found")

        module_names = {f.stem for f in src_files}
        graph: dict[str, set[str]] = {f.stem: set() for f in src_files}
        for fpath in src_files:
            imports = _extract_imports(fpath)
            for imp in imports:
                parts = imp.split(".")
                for part in parts:
                    if part in module_names and part != fpath.stem:
                        graph[fpath.stem].add(part)

        visited: set[str] = set()
        in_stack: set[str] = set()
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            in_stack.add(node)
            path.append(node)
            for neighbor in graph.get(node, set()):
                if neighbor in in_stack:
                    cycle_start = path.index(neighbor)
                    cycles.append([*path[cycle_start:], neighbor])
                elif neighbor not in visited:
                    dfs(neighbor, path)
            path.pop()
            in_stack.discard(node)

        for module in graph:
            if module not in visited:
                dfs(module, [])

        assert not cycles, "ARCH-02: Circular imports detected:\n" + "\n".join(f"  {' -> '.join(c)}" for c in cycles)


class TestNoRelativeImportEscapes:
    """ARCH-03: Relative imports must not escape package boundaries."""

    def test_no_deep_relative_imports(self):
        """No level-3+ relative imports allowed."""
        violations: list[str] = []
        for fpath in _python_files_in(PACKAGE_DIR):
            try:
                tree = ast.parse(fpath.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level and node.level > 2:
                    violations.append(
                        f"  {fpath.relative_to(ROOT)}:{node.lineno}: " f"level-{node.level} relative import"
                    )
        assert not violations, "ARCH-03: Deep relative imports detected:\n" + "\n".join(violations)


class TestScriptsNoTestImports:
    """ARCH-04: scripts/ must not import from tests/."""

    def test_no_test_imports_in_scripts(self):
        """scripts/ must not depend on test infrastructure."""
        violations: list[str] = []
        for fpath in _python_files_in(SCRIPTS_DIR):
            content = fpath.read_text(encoding="utf-8")
            if re.search(r"from\s+tests\b|import\s+tests\b", content):
                violations.append(str(fpath.relative_to(ROOT)))
        assert not violations, "ARCH-04: Scripts importing from tests/:\n" + "\n".join(f"  {v}" for v in violations)
