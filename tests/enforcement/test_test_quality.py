"""Test quality enforcement.

Criteria enforced:
  TQUAL-01: tests/ directory structure exists
  TQUAL-02: Every test file contains assert statements
  TQUAL-03: Test functions follow test_* naming convention
  TQUAL-04: conftest.py files provide shared fixtures
  TQUAL-05: Test files have module-level docstrings
  TQUAL-06: @pytest.mark.parametrize is used for data-driven tests

Run with:  pytest tests/enforcement/test_test_quality.py -v
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from .conftest import ROOT

TESTS_DIR = ROOT / "tests"
ENFORCEMENT_DIR = TESTS_DIR / "enforcement"


def _test_files_in(directory: Path) -> list[Path]:
    """All test_*.py files in a directory tree."""
    if not directory.exists():
        return []
    results = []
    for p in directory.rglob("test_*.py"):
        if "__pycache__" in str(p):
            continue
        results.append(p)
    return sorted(results)


class TestDirectoryStructure:
    """TQUAL-01: Required test directories must exist."""

    def test_enforcement_dir_exists(self):
        """tests/enforcement/ must exist."""
        assert ENFORCEMENT_DIR.exists() and ENFORCEMENT_DIR.is_dir(), "TQUAL-01: tests/enforcement/ directory missing"

    def test_tests_has_init(self):
        """tests/__init__.py must exist."""
        assert (TESTS_DIR / "__init__.py").exists(), "TQUAL-01: tests/__init__.py missing"


class TestAssertStatementsPresent:
    """TQUAL-02: Every test file must contain assert statements."""

    @staticmethod
    def _all_test_files() -> list[Path]:
        return _test_files_in(TESTS_DIR)

    @pytest.mark.parametrize(
        "test_file",
        _all_test_files.__func__(),
        ids=[str(f.relative_to(ROOT)) for f in _all_test_files.__func__()],
    )
    def test_file_has_asserts(self, test_file: Path):
        """Each test file must have assertion statements."""
        content = test_file.read_text(encoding="utf-8")
        has_assert = "assert " in content or "pytest.fail" in content
        assert has_assert, f"TQUAL-02: {test_file.relative_to(ROOT)} has no assert statements"


class TestFunctionNaming:
    """TQUAL-03: All test functions must start with test_."""

    def test_all_test_functions_named_correctly(self):
        """Methods in Test* classes must follow naming conventions."""
        issues: list[str] = []
        for fpath in _test_files_in(TESTS_DIR):
            try:
                tree = ast.parse(fpath.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and not item.name.startswith(
                            ("test_", "_", "setup", "teardown")
                        ):
                            issues.append(f"  {fpath.relative_to(ROOT)}:{item.lineno}: " f"{node.name}.{item.name}")
        assert not issues, "TQUAL-03: Methods in Test* classes not following naming:\n" + "\n".join(issues)


class TestConftestFixtures:
    """TQUAL-04: conftest.py files should provide shared fixtures."""

    def test_enforcement_conftest_exists(self):
        """tests/enforcement/conftest.py must exist."""
        conftest = ENFORCEMENT_DIR / "conftest.py"
        assert conftest.exists(), "TQUAL-04: tests/enforcement/conftest.py missing"

    def test_enforcement_conftest_has_content(self):
        """Enforcement conftest must have fixtures or constants."""
        conftest = ENFORCEMENT_DIR / "conftest.py"
        if not conftest.exists():
            pytest.skip("conftest.py missing")
        content = conftest.read_text(encoding="utf-8")
        assert (
            "@pytest.fixture" in content or "ROOT" in content
        ), "TQUAL-04: enforcement conftest.py has no fixtures or constants"


class TestDocstringsPresent:
    """TQUAL-05: Enforcement test files must have module-level docstrings."""

    def test_enforcement_files_have_docstrings(self):
        """All enforcement test files must document their purpose."""
        missing: list[str] = []
        for fpath in _test_files_in(ENFORCEMENT_DIR):
            try:
                tree = ast.parse(fpath.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            docstring = ast.get_docstring(tree)
            if not docstring:
                missing.append(str(fpath.relative_to(ROOT)))
        assert not missing, "TQUAL-05: Enforcement test files missing module docstrings:\n" + "\n".join(
            f"  {m}" for m in missing
        )


class TestParametrizeUsage:
    """TQUAL-06: Enforcement tests should use @pytest.mark.parametrize."""

    MIN_PARAMETRIZE_USAGES = 3

    def test_sufficient_parametrize_usage(self):
        """Enforcement suite must use data-driven tests."""
        count = 0
        for fpath in _test_files_in(ENFORCEMENT_DIR):
            content = fpath.read_text(encoding="utf-8")
            count += len(re.findall(r"@pytest\.mark\.parametrize", content))
        assert count >= self.MIN_PARAMETRIZE_USAGES, (
            f"TQUAL-06: Only {count} @pytest.mark.parametrize usages, " f"need >= {self.MIN_PARAMETRIZE_USAGES}"
        )
